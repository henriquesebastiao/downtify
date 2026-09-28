#!/bin/sh
# Probe for the Docker HEALTHCHECK instruction (see Dockerfile).
#
# Enabled by default. Set DOWNTIFY_HEALTHCHECK=0 to disable it — the
# check then always reports healthy without touching the server, for
# setups where an external/orchestrator-level check (e.g. a Kubernetes
# liveness probe) should be the only one deciding container health.
case "$(printf '%s' "${DOWNTIFY_HEALTHCHECK:-1}" | tr '[:upper:]' '[:lower:]')" in
    0 | false | no | off) exit 0 ;;
esac

# The port the server listens on: DOWNTIFY_PORT, else what it wrote at
# start (it may come from Settings), else the default.
PORT="${DOWNTIFY_PORT:-$(cat /tmp/downtify.port 2>/dev/null)}"
wget -q -O /dev/null "http://127.0.0.1:${PORT:-8000}/api/health"
