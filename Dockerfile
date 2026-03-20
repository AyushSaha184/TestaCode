FROM node:20-alpine AS frontend-build

WORKDIR /frontend

ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_API_TIMEOUT_MS=30000

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_TIMEOUT_MS=${VITE_API_TIMEOUT_MS}

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY database ./database
COPY generated_tests ./generated_tests
COPY src ./src
COPY .env.example ./.env.example
COPY frontend/nginx.conf /etc/nginx/sites-available/default
COPY --from=frontend-build /frontend/dist /usr/share/nginx/html

RUN mkdir -p /app/logs

EXPOSE 8000 80

CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port 8000 & nginx -g 'daemon off;'"]
