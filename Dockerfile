FROM python:3.12-slim

# Install iputils-ping for ping command
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy application
COPY src/main.py .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=1 \
    CMD cat /tmp/health_status 2>/dev/null | grep -q "healthy" || exit 1

# Switch to non-root user
USER appuser

ENTRYPOINT ["python3", "main.py"]
