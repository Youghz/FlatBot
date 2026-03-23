# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Install Python dependencies
FROM python:3.12-slim AS backend-build
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY flat_research/ flat_research/
COPY alembic/ alembic/
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# Stage 3: Web service (API + static frontend)
FROM python:3.12-slim AS web
WORKDIR /app
COPY --from=backend-build /app ./
COPY --from=frontend-build /app/frontend/dist ./static
COPY config.yaml ./
EXPOSE 8080
ENTRYPOINT [".venv/bin/python", "-m", "flat_research", "--serve"]

# Stage 4: Scraper job
FROM python:3.12-slim AS scraper
WORKDIR /app
COPY --from=backend-build /app ./
COPY config.yaml ./
ENTRYPOINT [".venv/bin/python", "-m", "flat_research", "--scrape-multi"]
