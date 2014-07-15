#!/usr/bin/env bash
set -e

function warn()
{
    echo "WARN: $@"
}

if [ ! -e $SRC_BASE/FrameworkBenchmarks ]; then
    git clone https://github.com/tgrabiec/FrameworkBenchmarks.git ${SRC_BASE}/FrameworkBenchmarks
else
    cd ${SRC_BASE}/FrameworkBenchmarks
    git fetch
    git checkout -f origin/master
fi

echo "Checking out OSv"

if [ ! -e $SRC_BASE/osv ]; then
    git clone https://github.com/cloudius-systems/osv.git ${SRC_BASE}/osv
    cd ${SRC_BASE}/osv
    git submodule update --init
else
    cd ${SRC_BASE}/osv
    git fetch
    git checkout -f ${OSV_VERSION_REF:-origin/master}
    git submodule update --init -f
fi


echo "Making tomcat module"

cd ${SRC_BASE}/osv/apps/tomcat
make clean || warn "make clean failed"
make

echo "Building the test app"

cd ${SRC_BASE}/FrameworkBenchmarks
git fetch
git checkout -f ${TEST_APP_VERSION_REF:-origin/master}
cd servlet
mvn clean install

echo "Building OSv image"

cd ${SRC_BASE}/osv
rm -rf build/release
make clean
make image=tomcat

echo "Copying test app to tomcat module"

cp ${SRC_BASE}/FrameworkBenchmarks/servlet/target/servlet.war ${SRC_BASE}/osv/apps/tomcat/ROOTFS/usr/tomcat/webapps
make image=tomcat

cd ${SRC_BASE}/osv

echo "Done."
