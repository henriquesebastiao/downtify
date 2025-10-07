#!/bin/sh

exec python main.py web --host 0.0.0.0 --port "${DOWNTIFY_PORT}" --keep-alive --web-use-output-dir --keep-sessions --client-id "${CLIENT_ID}" --client-secret "${CLIENT_SECRET}"