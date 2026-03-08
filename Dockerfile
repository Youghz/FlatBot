FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY config.yaml main.py sheets.py notifier.py http_client.py ./
COPY scrapers/ scrapers/

ENTRYPOINT ["uv", "run", "python", "main.py"]
