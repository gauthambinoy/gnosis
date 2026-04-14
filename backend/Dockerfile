# Stage 1: Build dependencies
FROM python:3.12-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Production image
FROM python:3.12-slim
WORKDIR /app

# Security: non-root user
RUN groupadd -r gnosis && useradd -r -g gnosis gnosis

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy app code
COPY . .

# Own files
RUN chown -R gnosis:gnosis /app

USER gnosis

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools"]
