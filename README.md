# korean-pii
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688?logo=fastapi&logoColor=white)
![KoELECTRA](https://img.shields.io/badge/KoELECTRA-small--v3--modu--ner-5C6BC0?logo=huggingface&logoColor=white)
![Presidio](https://img.shields.io/badge/Presidio-2.2.360-7B68EE?logo=windows&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.2-2563EB?logo=paddlepaddle&logoColor=white)
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
```bash
http://<host>:8000/pii/swagger
```


---


## 2. Additional Settings

### 2.1 Docker Base Image
> Point the python base image to internal registry (Dockerfile)
```dockerfile
ARG UV_IMAGE=<registry-endpoint>/astral-sh/uv:python3.12-bookworm-slim
FROM ${UV_IMAGE} AS runtime
```

### 2.2 Package Mirrors
> Swap package index to match environment (pyproject.toml)
```toml
[[tool.uv.index]]
name = "pytorch-cpu"
url = "http://<internal-mirror>/pypi" # Nexus Proxy Mirror
verify_ssl = false
explicit = true
```

### 2.3 Package Proxy
> Replace the source/sdist/wheels URLs with the proxy URLs (uv.lock)
```uv
[[package]]
name = "package-name"
version = "package-version"
source = { registry = "https://<registry-url>/simple" }
sdist = { url = "https://<registry-url>/packages/.../annotated_types-0.7.0.tar.gz", ... }
wheels = [
    { url = "https://<registry-url>/packages/.../annotated_types-0.7.0-py3-none-any.whl", ..." },
]
```
