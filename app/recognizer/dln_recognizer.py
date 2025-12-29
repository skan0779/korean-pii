import re
from datetime import datetime
from typing import Tuple, List

# 운전면허번호
def DriverLicenseRecognizer(text: str) -> Tuple[bool, str, List[str]]:
    """
    운전면허번호 탐지 및 치환.

    반환:
    - check : True/False
    - masked_user_query : str
    
    정책:
    - 지역코드(숫자): 2자리 (11~26)
    - 발급연도(숫자): 2자리 (1980~현재)
    - 일련번호(숫자): 6자리 (000000 금지)
    - 체크섬 + 재발급 횟수(숫자): 2자리 (0~9 + 0~9)
    """
    pattern = re.compile(
        r"(?<!\d)(\d{2})(?:\s*-\s*|\s+)(\d{2})(?:\s*-\s*|\s+)"
        r"(\d{6})(?:\s*-\s*|\s+)(\d)(\d)(?!\d)"
    )
    allowed_regions = {str(i) for i in range(11, 27)}
    now = datetime.now()
    curr_yy = now.year % 100
    detected = False

    def _repl(m: re.Match) -> str:
        nonlocal detected
        region, yy, serial, chk, turn = m.groups()
        if region not in allowed_regions:
            return m.group(0)
        y = int(yy)
        year = (2000 + y) if y <= curr_yy else (1900 + y)
        if year < 1980 or year > now.year:
            return m.group(0)
        if serial == "000000":
            return m.group(0)
        detected = True
        return "[운전면허번호]"

    text = pattern.sub(_repl, text)
    return detected, text, (["운전면허번호"] if detected else [])
