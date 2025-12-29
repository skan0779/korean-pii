from pydantic import BaseModel
from typing import List
from pathlib import Path
# --- module ---
from app.pii_main import pii_pipeline
from app.pii_ocr import pii_ocr_single
# --- FastAPI ---
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)

# --- FastAPI 앱 초기화 ---
app = FastAPI(
    title="Korean PII API",
    version="1.0.0",
    docs_url=None,
    openapi_url="/pii/openapi.json",
    redoc_url=None,
    swagger_ui_oauth2_redirect_url="/pii/swagger/oauth2-redirect",
)

# --- Swagger UI 설정 ---
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/pii/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/pii/swagger", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
    return get_swagger_ui_html(
        openapi_url=request.url_for("openapi").path,
        title="MeritzFire GPT PII - Swagger UI",
        oauth2_redirect_url=request.url_for("swagger_ui_redirect").path,
        swagger_js_url=request.url_for("static", path="swagger-ui-bundle.js").path,
        swagger_css_url=request.url_for("static", path="swagger-ui.css").path,
        swagger_favicon_url=request.url_for("static", path="favicon.png").path,
    )

@app.get("/pii/swagger/oauth2-redirect", include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

# --- 1. /pii/ping ---

class PingResponse(BaseModel):
    ping: bool = True

@app.get("/pii/ping", response_model=PingResponse, tags=["Ping"])
async def ping():
    return JSONResponse({"ping": True})


# --- 2. /pii/text ---

class In(BaseModel):
    text: str

class Out(BaseModel):
    blocked: bool
    masked_text: str
    label_list: list[str]
    reason: str

@app.post("/pii/text", response_model=Out)
def analyze(inp: In):
    blocked, masked_text, labels, reason = pii_pipeline(inp.text)

    return Out(
        blocked=blocked, 
        masked_text=masked_text, 
        label_list=labels,
        reason=reason
    )

# --- 3. /pii/image ---

@app.post("/pii/image", response_model=Out)
async def analyze_image(files: List[UploadFile] = File(...)):

    for file in files:
        content = await file.read()
        extracted_text = pii_ocr_single(content)
        blocked, masked_text, labels, reason = pii_pipeline(extracted_text)

        if blocked:
            print(f"[PII DETECTED] IMAGE : {blocked} / {masked_text} / {labels} / {reason}")
            return Out(
                blocked=blocked,
                masked_text="",
                label_list=labels,
                reason=reason
            )

    return Out(
        blocked=False,
        masked_text="",
        label_list=[],
        reason=""
    )
