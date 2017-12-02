#!/usr/bin/env bash
python3 server.py &
CACHE_PID=$!
sleep 1

gunicorn -w 2 -t 3 example:app &
HTTPD_PID=$!
sleep 1

ab -c 2 -t 3 http://localhost:8000/fib/cache/20

kill $CACHE_PID
kill $HTTPD_PID

wait
