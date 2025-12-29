import re
from datetime import datetime
from typing import Tuple, List

# 외국인등록번호
def AlienRegistrationRecognizer(text: str) -> Tuple[bool, str, List[str]]:
    """
    외국인등록번호를 탐지 및 치환.

    반환:
    - arn_detected : True/False
    - masked_user_query : str

    정책:
    - 날짜 유효성 검사
    - 출생일 < 2020-10-01 : 체크섬 적용
    - 출생일 >= 2020-10-01 : 체크섬 미적용
    """
    pattern = re.compile(r"(?<!\d)(\d{6})[-\s]?([5-8]\d{6})(?!\d)")
    cutoff = datetime(2020, 10, 1)
    detected = False

    def _repl(m: re.Match) -> str:
        nonlocal detected
        front, back = m.group(1), m.group(2)
        seventh = back[0]
        # 날짜 유효성
        try:
            yy, mm, dd = int(front[:2]), int(front[2:4]), int(front[4:6])
            year = (1900 if seventh in "12" else 2000) + yy
            birth = datetime(year, mm, dd)
        except Exception:
            return m.group(0)
        
        # 체크섬 (2020-10 이전)
        if birth < cutoff:
            digits = [int(c) for c in (front + back)]
            weights = [2,3,4,5,6,7,8,9,2,3,4,5]
            s = sum(d * w for d, w in zip(digits[:12], weights))
            if (11 - (s % 11)) % 10 != digits[12]:
                return m.group(0)
        detected = True
        return "[외국인등록번호]"

    text = pattern.sub(_repl, text)
    return detected, text, (["외국인등록번호"] if detected else [])
