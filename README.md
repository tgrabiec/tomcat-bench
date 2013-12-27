Tomcat performance testing
=========================


## Preparing host machine


Checkout OSv

```sh
cd ~/src/osv
git checkout ${OSV_VERSION}
git submodule update
```

Build the test app

```sh
cd ~/src
git clone https://github.com/tgrabiec/FrameworkBenchmarks.git
git checkout ${TEST_APP_VERSION}
cd FrameworkBenchmarks/servlet
mvn clean install
```

Checkout tomcat module

```sh
cd apps
git remote add tgrabiec https://github.com/tgrabiec/osv-apps.git
git fetch tgrabiec
git checkout 93bc7f65fec70a754657868650a79d719ff92772
```

Copy test app to tomcat module

```sh
cp ~/src/FrameworkBenchmarks/servlet/target/servlet.war ~/src/osv/apps/tomcat/upstream/apache-tomcat-${TOMCAT_VERSION}/webapps/
```

Build the image
```sh
cd ~/src/osv
make image=tomcat
```

Save the image to a backup file

```sh
cp build/release/usr.img usr.img.original
```

## Preparing load driver machine

Checkout benchmark scripts

```sh
cd ~/src
git clone https://github.com/tgrabiec/tomcat-bench
cd tomcat-bench
```

Apply system configuration

```sh
sudo ./setup.sh
```

## Running the test on OSv

Start OSv

```sh
cp usr.img.original build/release/usr.img
sudo scripts/run.py -m4g -nv -b bridge0
```

Read the printed IP of OSv and assign to `GUEST_IP` variable.

Warm up

```sh
wrk --latency -t4 -c256 -d30s http://${GUEST_IP}:8081/servlet/json
```

Perform the test

```sh
wrk --latency -t4 -c128 -d1m http://${GUEST_IP}:8081/servlet/json | tee wrk.out
```

Parse the output

```sh
./wrk-parse.py wrk.out
```


## After test

Restore system configuration on load driver machine

```sh
cd ~/src/tomcat-bench
sudo ./restore_sys_conf.sh
```

### Obtaining test variables

Host:

```sh
cd ~/src/osv
OSV_VERSION=$(git rev-parse HEAD)
cd apps
APPS_VERSION=$(git rev-parse HEAD)
```

```sh
cd ~/src/FrameworkBenchmarks
TEST_APP_VERSION=$(git rev-parse HEAD)
```

Load driver:

```sh
cd ~/src/tomcat-bench
TOMCAT_BENCHMARK_VERSION=$(git rev-parse HEAD)
```
