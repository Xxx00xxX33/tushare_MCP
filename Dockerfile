# Sidecar (required by Smithery)
FROM registry.depot.dev/dsk57gtb7p:http-sidecar AS sidecar_image

# App image
FROM python:3.10-slim AS stage-1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Then copy source code
COPY . .

# Entry (MCP process mode)
CMD ["python", "server.py"]
