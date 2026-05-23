FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into the system Python (no venv inside container)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the source
COPY . .

# Install the project itself
RUN uv sync --frozen --no-dev
