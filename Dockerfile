# MSSclaw Docker 镜像
# 用法:
#   docker build -t mssclaw .
#   docker run -p 5099:5099 -v ~/.mssclaw:/root/.mssclaw mssclaw

FROM python:3.11-slim

LABEL org.mssclaw.version="1.0.0"
LABEL org.mssclaw.description="MSS-AI Agent Framework"

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install mssclaw
COPY . .
RUN pip install -e . --no-deps

# Vault data volume
VOLUME ["/root/.mssclaw"]

# Default: run vault server
EXPOSE 5099
CMD ["python", "-m", "mssclaw.core.vault_cli", "serve", "--no-auth"]
