#!/bin/sh
# Запускает API и, если база пустая, заливает демо-данные.
set -e
uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips='*' &
API_PID=$!
python /scripts/seed.py --api "http://127.0.0.1:$PORT" || echo "Демо-данные не загрузились, сайт работает без них"
wait $API_PID
