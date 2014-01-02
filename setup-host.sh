#!/usr/bin/env bash
set -e

function warn()
{
    echo "WARN: $@"
}

SRC_BASE=~/src

if [ ! -e $SRC_BASE/FrameworkBenchmarks ]; then
    git clone https://github.com/tgrabiec/FrameworkBenchmarks.git ${SRC_BASE}/FrameworkBenchmarks
fi

if [ ! -e $SRC_BASE/osv ]; then
    git clone https://github.com/cloudius-systems/osv.git ${SRC_BASE}/osv
fi

cd ${SRC_BASE}/osv/apps
git remote add tgrabiec https://github.com/tgrabiec/osv-apps.git || warn "Failed to add remote"

echo "Checkout OSv"

cd ${SRC_BASE}/osv
git fetch
git checkout -f ${OSV_VERSION_REF:-origin/master}
git submodule update

echo "Building the test app"

cd ${SRC_BASE}/FrameworkBenchmarks
git fetch
git checkout -f ${TEST_APP_VERSION_REF:-origin/master}
cd servlet
mvn clean install

echo "Checking out tomcat module"

cd ${SRC_BASE}/osv/apps
git fetch tgrabiec
git checkout -f ${APPS_VERSION_REF:-tgrabiec/tomcat-perf}

echo "Copying test app to tomcat module"

cp ${SRC_BASE}/FrameworkBenchmarks/servlet/target/servlet.war ${SRC_BASE}/osv/apps/tomcat/upstream/*/webapps/

echo "Building OSv image"

cd ${SRC_BASE}/osv
rm -rf build/release
make clean
make external && make image=tomcat

echo "Saving the image to a backup file"

cp build/release/usr.img usr.img.original

echo "Done."
