FROM python:3.14-slim@sha256:6a27522252aef8432841f224d9baaa6e9fce07b07584154fa0b9a96603af7456

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY flat_research/ flat_research/
RUN uv sync --frozen --no-dev

COPY config.yaml ./

ENTRYPOINT ["uv", "run", "python", "-m", "flat_research"]
