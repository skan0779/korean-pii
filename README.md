# korean-pii
> Korean PII detection and redaction(masking) for text and images in an air-gapped environment (Dockerized, CPU-only)

---

## 1. Quick Start

### 1.1 Setup (uv)
> Use `uv` for dependency management.
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
uv sync  # Sync dependencies
```

### 1.2 Run Locally
> Start the FastAPI application
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 1.3 Run with Docker
> Build and run using the deployment compose file.
```bash
docker compose -f environments/deploy/docker-compose.yml up --build
```

### 1.4 Swagger API
> Swagger UI assets are bundled in `app/static` (load in air‑gapped environment)
> Open: http://<host>:8000/pii/swagger

---

## 2. Additional Settings

### 2.1 Docker base image
> Point the python base image to internal registry (Dockerfile)
```dockerfile
ARG UV_IMAGE=<registry-endpoint>/astral-sh/uv:python3.12-bookworm-slim
FROM ${UV_IMAGE} AS runtime
```

### 2.2 Package mirrors
> Swap package index to match environment (pyproject.toml)
```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "http://<internal-mirror>/pypi" # Nexus Proxy Mirror
verify_ssl = false
explicit = true
```
