FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

ENV PDM_USE_VENV=0

RUN pip install pdm

COPY pyproject.toml pdm.lock* README.md ./
COPY nedap_ons_uptime ./nedap_ons_uptime
RUN if [ -f pdm.lock ]; then pdm install --prod; else pdm install --prod --no-lock; fi

COPY . .

ENV DATABASE_URL=postgresql+asyncpg://uptime:uptime@postgres:5432/uptime
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV CONCURRENCY=20
ENV RETENTION_DAYS=35
ENV APP_TIMEZONE=Europe/Amsterdam
ENV AUTH_ENABLED=true
ENV AUTH_USERNAME=admin
ENV AUTH_PASSWORD=change-me
ENV SESSION_SECRET_KEY=change-me-session-secret
ENV SESSION_MAX_AGE=86400

EXPOSE 8000

CMD ["pdm", "run", "nedap-ons-uptime", "serve"]
