#!/usr/bin/env bash

RESTORE_FILE="restore_sys_conf.sh"

function recoverable_sysctl()
{
    local param=$1
    local value=$2

    echo "$(sysctl $param)" | sed 's/ //g' | xargs echo "sysctl" >> $RESTORE_FILE
    sysctl $param=$value || exit 1
}

if [ -e $RESTORE_FILE ]; then
    echo "=== Restoring previous config ==="
    (./$RESTORE_FILE && rm $RESTORE_FILE) || exit 1
fi

touch $RESTORE_FILE
chmod +x $RESTORE_FILE

echo "=== Configuring ==="
recoverable_sysctl net.ipv4.tcp_max_syn_backlog 65535
recoverable_sysctl net.core.somaxconn 65535
recoverable_sysctl net.ipv4.tcp_tw_reuse 1
recoverable_sysctl net.ipv4.tcp_tw_recycle 1

echo "==== Previous settings (saved to $RESTORE_FILE): ===="
cat $RESTORE_FILE
