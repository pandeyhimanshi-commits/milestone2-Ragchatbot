#!/bin/sh
# https://render.com/docs/web-services#port-binding
set -e
export PORT="${PORT:-10000}"
exec python -m uvicorn runtime_api.app:app --host 0.0.0.0 --port "$PORT"
