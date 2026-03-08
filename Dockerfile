FROM python:3.12-slim@sha256:ccc7089399c8bb65dd1fb3ed6d55efa538a3f5e7fca3f5988ac3b5b87e593bf0

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY config.yaml main.py sheets.py notifier.py http_client.py ./
COPY scrapers/ scrapers/

ENTRYPOINT ["uv", "run", "python", "main.py"]
