#!/usr/bin/env bash
set -e

function warn()
{
    echo "WARN: $@"
}

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

echo "Building OSv image"

cd ${SRC_BASE}/osv
rm -rf build/release
make clean
make image=tomcat-benchmark

cd ${SRC_BASE}/osv

echo "Done."
