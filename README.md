# korean-pii
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.121-009688?logo=fastapi&logoColor=white)
![KoELECTRA](https://img.shields.io/badge/KoELECTRA-small--v3--modu--ner-5C6BC0?logo=huggingface&logoColor=white)
![Presidio](https://img.shields.io/badge/Presidio-2.2.360-7B68EE?logo=windows&logoColor=white)
![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.2-2563EB?logo=paddlepaddle&logoColor=white)
> Korean PII detection and redaction(masking) for text and images in an air-gapped environment (Dockerized, CPU-only)

## PII Field
> 고유식별정보 탐지 이후 일반개인정보 조합 탐지 진행
| TAG | Categoary | Method | Policy |
| --- | --- | --- | --- |
| **주민등록번호** | 고유식별정보 | Regex + Checksum(행안부) | 단일 탐지 즉시 차단 |
| **외국인등록번호** | 고유식별정보 | Regex + Checksum(행안부) | 단일 탐지 즉시 차단 |
| **운전면허번호** | 고유식별정보 | Regex + Checksum(지역코드/발급년도) | 단일 탐지 즉시 차단 |
| **여권번호** | 고유식별정보 | Regex | 단일 탐지 즉시 차단 |
| **이름** | 일반개인정보 | NER(KoELECTRA) | 조합 탐지 시 차단 (이름 + 전화/이메일/계좌/카드/사업자번호) |
| **전화번호** | 일반개인정보  | Regex | 조합 탐지 시 차단 (전화 + 이름/이메일/계좌/카드) |
| **이메일** | 일반개인정보 | Presidio | 조합 탐지 시 차단(이메일 + 이름/전화/계좌/카드) |
| **계좌번호** | 일반개인정보 | Regex | 조합 탐지 시 차단(계좌 + 이름/전화/이메일/카드/사업자번호) |
| **카드번호** | 일반개인정보 | Presidio | 조합 탐지 시 차단(카드 + 이름/전화/이메일/계좌) |
| **사업자등록번호** | 일반개인정보 | Regex + Checksum(국세청) | 조합 탐지 시 차단(사업자 + 이름/계좌) |

## API
> FastAPI 
| TAG | API | Detail |
| --- | --- | --- |
| GET | **/pii/swagger** | Swagger UI |
| GET | **/pii/openapi.json** | OpenAPI |
| GET | **/pii/ping** | 서버 상태 확인 |
| POST | **/pii/text** | 텍스트 개인정보 탐지 및 마스킹 |
| POST | **/pii/image** | 이미지 개인정보 탐지  |

## Response Schema
| Field | Type | Description |
| --- | --- | --- |
| **blocked** | boolean | 차단 여부 |
| **masked_text** | string | 마스킹된 텍스트 |
| **label_list** | string[] | 탐지된 개인정보 목록 |
| **reason** | string | 차단 사유 (고유식별정보, 일반개인정보) |


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


## 2. Settings for air-gapped environment

### 2.1 Docker Base Image
> Point the python base image to internal registry (Dockerfile)
```dockerfile
ARG UV_IMAGE=<registry-endpoint>/astral-sh/uv:python3.12-bookworm-slim
FROM ${UV_IMAGE} AS runtime
```

### 2.2 Package Mirror
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
