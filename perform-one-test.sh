#!/usr/bin/env bash

if [ -z "$GUEST_IP" ]; then
    echo "Please set GUEST_IP"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Warmup ==="
wrk -t4 -c256 -d30s http://${GUEST_IP}:8081/servlet/json

echo "=== Main test ==="
wrk_out_file=wrk.${TIMESTAMP}
echo "Output goes to $wrk_out_file"
wrk --latency -t4 -c128 -d1m http://${GUEST_IP}:8081/servlet/json > ${wrk_out_file}

echo "=== Results ==="
./wrk-parse.py ${wrk_out_file}
