Tomcat performance testing
=========================

First checkout latest version of this repository on all machines

```sh
test -e ~/src/tomcat-bench || git clone https://github.com/tgrabiec/tomcat-bench ~/src/tomcat-bench
cd ~/src/tomcat-bench
git fetch
git checkout -f ${TOMCAT_BENCHMARK_VERSION_REF:-origin/master}
```

## Preparing host machine

Run

```sh
./setup-host.sh
```

### Prepare fedora image

TODO: Describe how to prepare base fedora image

Start your fedora image:

```sh
cd ~/src/osv
sudo scripts/run.py -m2g -nv -b bridge0 -i ~/fedora/fedora.img
GUEST_IP=10.0.0.176
```


Upload tomcat deployment to fedora guest
```sh
cd apps/tomcat/upstream
zip -r tomcat.zip apache-tomcat-7.0.42/
scp tomcat.zip root@${GUEST_IP}:~
```

On fedora guest, unzip the package and shut down

```sh
cd ~
rm -rf apache-tomcat-*/
unzip tomcat.zip
ln -s apache-tomcat-7.0.42 tomcat
shutdown now
```

Save image backup

```sh
cp ~/fedora/fedora.img ~/fedora/fedora.img.original 
```


## Preparing load driver machine

Run

```sh
sudo ./setup.sh
```


## Running the test

Restore image from the backup and start the guest.

For OSv:
```sh
cd ~/src/osv
cp usr.img.original build/release/usr.img && \
sudo scripts/run.py -m4g -nv -b bridge0
```

For Fedora:
```sh
cp ~/fedora/fedora.img.original ~/fedora/fedora.img && \
sudo scripts/run.py -m4g -nv -b bridge0 -i ~/fedora/fedora.img
```

Read the IP of OSv. On load driver machine assign the IP to `GUEST_IP` variable.

On fedora guest:
```osv
export JAVA_OPTS="-Xmx2g -Xms2g"
cd tomcat/bin
./startup.sh
```

Start the test on load driver machine:

```sh
./perform-one-test.sh
```

Kill the guest.



## After test

Restore system configuration on load driver machine

```sh
cd ~/src/tomcat-bench
sudo ./restore_sys_conf.sh
rm ./restore_sys_conf.sh
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
echo BENCHMARK_VERSION=$(git rev-parse HEAD)
```
