#!/bin/sh

LOG_LEVEL="${DOWNTIFY_LOG_LEVEL:-info}"

exec python main.py web \
    --host 0.0.0.0 \
    --port "${DOWNTIFY_PORT}" \
    --log-level "${LOG_LEVEL}"
