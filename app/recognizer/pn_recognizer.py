import re
from datetime import datetime
from typing import Tuple, List

# 여권번호
def PassportRecognizer(text: str) -> Tuple[bool, str, List[str]]:
    """
    여권번호 탐지 및 치환.

    반환:
    - detected : True/False
    - masked_user_query : str

    정책:
    - 여권종류: M,S,R,G,D,T
    - 일련번호: 8자리 숫자
    """
    pattern = re.compile(r"(?<![A-Z0-9])([MSRGDT])(\d{8})(?![A-Z0-9])", re.IGNORECASE)
    detected = False

    def _repl(m: re.Match) -> str:
        nonlocal detected
        if m.group(2) == "00000000":
            return m.group(0)
        detected = True
        return "[여권번호]"

    text = pattern.sub(_repl, text)
    return detected, text, (["여권번호"] if detected else [])

