# ReunionAI backend image — runs migrations then serves the FastAPI app.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/backend

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

# Migrations are idempotent; running them on startup keeps the stack one-command.
CMD ["sh", "-c", "alembic upgrade head && uvicorn 'app.main:create_app' --factory --host 0.0.0.0 --port 8000"]
# OCI labels: link the GHCR package back to this repo (permissions inherit,
# Actions workflows get automatic package access).
LABEL org.opencontainers.image.source="https://github.com/ipproyectosysoluciones/Administration-MeetingAI"
LABEL org.opencontainers.image.description="ReunionAI backend API — FastAPI multi-tenant platform"
LABEL org.opencontainers.image.licenses="MIT"
