# Base image
ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.12-bookworm-slim
FROM ${UV_IMAGE} AS runtime

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul \
    HF_HOME=/app/.cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HOME=/app \
    PATH="/app/.venv/bin:$PATH" \
    WEB_CONCURRENCY=2 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    KOELECTRA_ONNX_DIR=/app/models/koelectra-onnx \
    PADDLE_DET_DIR=/app/models/paddleocr/det/PP-OCRv5_mobile_det \
    PADDLE_REC_DIR=/app/models/paddleocr/rec/korean_PP-OCRv5_mobile_rec

# Working directory
WORKDIR /app

# Create user
RUN useradd -m -u 1000 appuser

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV UV_SKIP_WHEEL_FILENAME_CHECK=1
RUN uv venv --python 3.12 && \
    uv sync --frozen --no-editable --no-cache -vv && \
    rm -rf /tmp/uv-cache

# Copy model files
COPY models/koelectra-onnx/ /app/models/koelectra-onnx/
COPY models/paddleocr/ /app/models/paddleocr/

# Copy app code
COPY app ./app

# Create cache directory
RUN mkdir -p /app/.cache/huggingface

# Set permissions
RUN chown -R appuser:appuser /app

# Switch user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/pii/ping || exit 1

# Run app
CMD ["sh", "-c", "uv run --no-sync gunicorn \
    -k uvicorn.workers.UvicornWorker \
    -w ${WEB_CONCURRENCY} \
    -b 0.0.0.0:8000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 30 \
    --access-logfile - \
    --error-logfile - \
    app.main:app"]
