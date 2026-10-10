FROM python:3.12-slim

# Copy uv from its official image so dependency installation stays fast and
# reproducible from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install locked dependencies before application code, preserving this layer
# when only the source changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . ./
RUN uv sync --locked

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "src/traffic_api/main.py", "--host", "0.0.0.0", "--port", "8000"]
