Tomcat performance testing
=========================


## Preparing host machine

Setup repositories (first timers only)

```sh
git clone https://github.com/tgrabiec/FrameworkBenchmarks.git ~/src/FrameworkBenchmarks
git clone https://github.com/cloudius-systems/osv.git ~/src/osv
cd ~/src/osv/apps
git remote add tgrabiec https://github.com/tgrabiec/osv-apps.git
```

Checkout OSv

```sh
cd ~/src/osv
git fetch
git checkout ${OSV_VERSION_REF:-origin/master}
git submodule update
```

Build the test app

```sh
cd ~/src/FrameworkBenchmarks
git fetch
git checkout ${TEST_APP_VERSION_REF:-origin/master}
cd servlet
mvn clean install
```

Checkout tomcat module

```sh
git fetch tgrabiec
git checkout ${APPS_VERSION_REF:-tgrabiec/tomcat-perf}
```

Copy test app to tomcat module

```sh
cp ~/src/FrameworkBenchmarks/servlet/target/servlet.war ~/src/osv/apps/tomcat/upstream/apache-tomcat-${TOMCAT_VERSION}/webapps/
```

Build the image
```sh
cd ~/src/osv
make external && make image=tomcat
```

Save the image to a backup file

```sh
cp build/release/usr.img usr.img.original
```

## Preparing load driver machine

Clone benchmark scripts (first time only)

```sh
git clone https://github.com/tgrabiec/tomcat-bench ~/src/tomcat-bench
```

Checkout

```sh
cd ~/src/tomcat-bench
git fetch
git checkout ${TOMCAT_BENCHMARK_VERSION_REF:-origin/master}
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
sudo ./restore_sys_conf.sh && rm ./restore_sys_conf.sh
```

### Obtaining test variables

Host:

```sh
cd ~/src/osv
echo OSV_VERSION=$(git rev-parse HEAD)
cd apps
echo APPS_VERSION=$(git rev-parse HEAD)
```

```sh
cd ~/src/FrameworkBenchmarks
echo TEST_APP_VERSION=$(git rev-parse HEAD)
```

Load driver:

```sh
cd ~/src/tomcat-bench
echo TOMCAT_BENCHMARK_VERSION=$(git rev-parse HEAD)
```
