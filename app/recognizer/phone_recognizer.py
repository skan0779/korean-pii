from typing import List
from presidio_analyzer import EntityRecognizer, RecognizerResult
import re

# 전화번호 (11자리)
class KRPhoneRecognizer(EntityRecognizer):
    """
    한국 휴대폰번호(PII) 전용 인식기:

    허용: 
    - 010-4871-0779
    - 010 4871 0779
    - 01048710779
    - +82 10-4871-0779

    제외: 
    - 유선: 02
    - 대표번호: 15xx/16xx/18xx
    - 인터넷전화: 070
    - 안심번호: 050
    - 2G번호: 011/016/017/018/019
    - 반복열: 000/111/999
    - "0000"
    """
    def __init__(self):
        super().__init__(supported_entities=["KR_PHONE_NUMBER"], supported_language="en")
        self.candidate = re.compile(r"""
            (?<![\d(])                              # 왼쪽에 숫자 배제
            (?:                                     # 허용 포맷 묶음
                010-\d{4}-\d{4}                     # 010-1234-5678
              | 010\ \d{4}\ \d{4}                   # 010 1234 5678
              | 010\d{8}                            # 01012345678
              | \+82\ 10-\d{4}-\d{4}                # +82 10-1234-5678
              | \+82\ 10\d{8}                       # +82 1012345678
              | \+82\ 10\ \d{4}\ \d{4}              # +82 10 1234 5678
            )
            (?!\d)                                   # 오른쪽에 숫자 금지
        """, re.VERBOSE)

    @staticmethod
    def _digits(s: str) -> str:
        return re.sub(r"\D", "", s)

    @staticmethod
    def _normalize_kr(d: str) -> str:
        return ("0" + d[2:]) if d.startswith("82") else d

    @staticmethod
    def _looks_bad(d: str) -> bool:
        """
        반복열 배제 규칙:
        - 끝 4자리가 0000 (예: 010-1234-0000)
        - 뒤 8자리가 모두 같은 숫자 (예: 010-1111-1111, 010-9999-9999)
        - 4자리 반복(앞 4 == 뒤 4, 예: 010-1234-1234)
        """
        tail = d[3:]                  
        if tail.endswith("0000"):
            return True
        if len(set(tail)) == 1:
            return True
        if tail[:4] == tail[4:]:
            return True
        return False
    
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:

        if "KR_PHONE_NUMBER" not in entities or not text:
            return []

        out: List[RecognizerResult] = []
        for m in self.candidate.finditer(text):
            raw = m.group(0)
            d = self._normalize_kr(self._digits(raw))

            if not (d.startswith("010") and len(d) == 11):
                continue
            if self._looks_bad(d):
                continue

            out.append(RecognizerResult("KR_PHONE_NUMBER", m.start(), m.end(), score=0.9))
            
        return out
