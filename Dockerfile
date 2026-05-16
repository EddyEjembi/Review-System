# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/go/dockerfile-reference/

# Want to help us make this template better? Share your feedback here: https://forms.gle/ybq9Krt8jtBL3iCk7
ARG PYTHON_IMAGE_TAG=3.12-slim-bookworm
FROM python:${PYTHON_IMAGE_TAG}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Layer cache: lockfile + deps only (no packaging of this repo as a wheel).
# Plain `uv sync` (no BuildKit cache mount): works on Docker Desktop and Railway.
# Railway requires id=s/<service-id>-<path> on cache mounts; that is not portable in git.
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Writable cache for Hugging Face Hub (SentenceTransformer): appuser has HOME=/nonexistent by default.
RUN mkdir -p /app/.cache/huggingface && chown -R appuser:appuser /app

# Switch to the non-privileged user to run the application.
USER appuser

ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/app \
    HF_HOME=/app/.cache/huggingface \
    XDG_CACHE_HOME=/app/.cache

# Expose the port that the application listens on.
EXPOSE 9000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-9000}"]
