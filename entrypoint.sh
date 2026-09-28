#!/bin/sh

LOG_LEVEL="${DOWNTIFY_LOG_LEVEL:-info}"

# No --port: main.py takes DOWNTIFY_PORT when it's set, else the port
# chosen in Settings > Server, else 8000 (downtify/server_port.py).
exec python main.py web \
    --host 0.0.0.0 \
    --log-level "${LOG_LEVEL}"
