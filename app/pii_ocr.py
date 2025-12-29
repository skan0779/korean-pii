import io, os, re
import logging
from pathlib import Path
from paddleocr import PaddleOCR
from typing import Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Model Directory
ROOT = Path(__file__).resolve().parents[1]
DET_DIR = os.getenv("PADDLE_DET_DIR", str(ROOT / "models" / "paddleocr" / "det" / "PP-OCRv5_mobile_det"))
REC_DIR = os.getenv("PADDLE_REC_DIR", str(ROOT / "models" / "paddleocr" / "rec" / "korean_PP-OCRv5_mobile_rec"))

# Image Resize
MAX_IMAGE_SIZE = 1536
MAX_IMAGE_PIXELS = int(str(5 * 1024 * 1024))

# PaddleOCR
try:
    ocr = PaddleOCR(
        # CPU 설정
        device='cpu',
        enable_mkldnn=True,
        cpu_threads=2,
        # 모델 설정
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_detection_model_dir=DET_DIR,
        text_recognition_model_name="korean_PP-OCRv5_mobile_rec",
        text_recognition_model_dir=REC_DIR,
        # 기타 설정
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    
except Exception as e:
    logger.exception("Failed to initialise PaddleOCR: %s", e)
    print(f"[OCR ERROR] PaddleOCR initialization failed: {e}")
    raise

def resize_image_for_ocr(image: Image.Image, max_size: int = MAX_IMAGE_SIZE) -> Tuple[Image.Image, float]:
    """
    OCR 처리를 위해 이미지 크기 조정
    
    Args:
        image: PIL Image 객체
        max_size: 최대 허용 크기 (가로 또는 세로의 최대값)
    
    Returns:
        (리사이즈된 이미지, 스케일 비율)
    """
    width, height = image.size
    total_pixels = width * height
    scale_ratio = 1.0
    
    # 전체 픽셀 수 체크
    if total_pixels > MAX_IMAGE_PIXELS:
        scale_ratio = np.sqrt(MAX_IMAGE_PIXELS / total_pixels)
        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)
        logger.info(f"Resizing due to pixel count: {width}x{height} -> {new_width}x{new_height}")
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        width, height = new_width, new_height
    
    # 최대 크기 체크
    if width > max_size or height > max_size:
        dimension_scale = max_size / max(width, height)
        new_width = int(width * dimension_scale)
        new_height = int(height * dimension_scale)
        logger.info(f"Resizing due to dimension limit: {width}x{height} -> {new_width}x{new_height}")
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        scale_ratio *= dimension_scale
    
    return image, scale_ratio

def normalize_ocr_text(text: str) -> str:
    """
    OCR 텍스트 정규화: 
    
    숫자/하이픈 사이의 공백 제거:
    - "079301 -04 - 061985" -> "079301-04-061985"
    - "010 - 1234 - 5678" -> "010-1234-5678"
    - "123 - 45 - 67890" -> "123-45-67890"
    """
    def remove_spaces(match):
        return match.group(0).replace(' ', '')
    
    pattern = r'\d[\d\s\-]+\d'
    normalized = re.sub(pattern, remove_spaces, text)
    return normalized

def pii_ocr_single(image_bytes: bytes) -> str:
    """단일 이미지에서 텍스트 추출"""
    try:
        with io.BytesIO(image_bytes) as bio:
            with Image.open(bio) as image:
                original_size = image.size
                logger.info("[OCR INFORMATION] Original size=%s mode=%s", original_size, image.mode)

                # RGB 변환
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # OOM 방지를 위한 이미지 리사이즈
                image, scale_ratio = resize_image_for_ocr(image)
                if scale_ratio != 1.0:
                    logger.info("[OCR RESIZE] Scaled by %.2f, New size=%s", scale_ratio, image.size)
                
                # numpy array 변환
                img_array = np.array(image)
                
                # OCR 수행
                try:
                    result = ocr.predict(img_array)
                except Exception as ocr_error:
                    logger.warning("[OCR WARNING] OCR failed, retrying with smaller size: %s", ocr_error)
                    smaller_image, _ = resize_image_for_ocr(image, max_size=MAX_IMAGE_SIZE // 2)
                    result = ocr.predict(np.array(smaller_image))

                # 텍스트 추출
                texts = []
                if result and isinstance(result, list):
                    for res in result:
                        js = getattr(res, "json", None)
                        if isinstance(js, dict):
                            core = js.get("res", js)
                            for t in core.get("rec_texts", []) or []:
                                if t and t.strip():
                                    texts.append(t.strip())
                    
                if texts:
                    full_text = ' '.join(texts)
                    normalized_text = normalize_ocr_text(full_text)
                    logger.info("[OCR RESPONSE] Text detected (length=%d)", len(normalized_text))
                    return normalized_text
                
                logger.info("[OCR RESPONSE] No text detected")
                return ""
    except Exception as e:
        logger.exception("[OCR ERROR] %s", e)
        return ""
