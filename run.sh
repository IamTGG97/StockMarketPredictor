#!/bin/sh
cd /var/task
exec python3.12 -m gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 2 --timeout 28 app:app
