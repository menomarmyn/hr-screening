# Деплой одним контейнером: FastAPI отдаёт и API, и собранный сайт.
# Используется для Render (render.yaml). Для локальной разработки — docker-compose.yml.
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_DEMO=true
ENV VITE_DEMO=$VITE_DEMO
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 STATIC_DIR=/app/static PORT=8000
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/eval ./eval
COPY data /data
COPY scripts /scripts
COPY deploy/entrypoint.sh /entrypoint.sh
COPY --from=web /web/dist ./static
RUN chmod +x /entrypoint.sh && useradd -m appuser
USER appuser
EXPOSE 8000
CMD ["/entrypoint.sh"]
