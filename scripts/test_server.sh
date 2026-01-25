#!/usr/bin/env bash
set -euo pipefail
HOST_URL=${1:-http://127.0.0.1:8000/healthz}
TIMEOUT=${2:-120}

python manage.py runserver 127.0.0.1:8000 &
SERVER_PID=$!

echo "Waiting for healthz at $HOST_URL"
END=$((SECONDS+TIMEOUT))
while [ $SECONDS -lt $END ]; do
  if curl -s -o /dev/null -w "%{http_code}" "$HOST_URL" | grep -q "200"; then
    echo "Server is ready (pid=$SERVER_PID)"
    exit 0
  fi
  sleep 2
done

echo "Server did not become ready in time"
kill $SERVER_PID || true
exit 1
