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

Perform the following steps in fedora guest.

Unzip the package:

```sh
$ cd ~
$ rm -rf apache-tomcat-*/
$ unzip tomcat.zip
$ ln -s apache-tomcat-7.0.42 tomcat
```

Create init script and shutdown:
  
```sh
$ cd /etc/init.d
$ cat > tomcat
#!/bin/bash
set -e
case $1 in
    'start')
        export JAVA_OPTS="-Xmx2g -Xms2g"
        cd /root/tomcat/bin
        ./startup.sh 2>&1 > /var/log/tomcat.log < /dev/null &
    ;;
esac
$ chmod +x tomcat 
$ cd ../rc3.d
$ ln -s ../init.d/tomcat S99tomcat
$ shutdown now
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

Restore image from the backup and start the guest. It is important to do it before each test
because the guest file system fills up very quickly. If the image was not restored the consecutive samples would not be independent.

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

Read the IP of OSv and assign to `GUEST_IP` variable on **load driver** machine.

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
echo OSV_VERSION=$(scripts/osv-version.sh)
cd apps
echo APPS_VERSION=$(git rev-parse HEAD)
```

```sh
cd ~/src/FrameworkBenchmarks
echo TEST_APP_VERSION=$(git rev-parse HEAD)
```

```sh
echo QEMU_VERSION=$(qemu-system-x86_64 -version | sed -r 's/.*version ([0-9.]+).*/\1/')
```

Load driver:

```sh
cd ~/src/tomcat-bench
echo BENCHMARK_VERSION=$(git rev-parse HEAD)
```
