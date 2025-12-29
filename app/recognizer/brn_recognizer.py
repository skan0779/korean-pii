from typing import List
from presidio_analyzer import EntityRecognizer, RecognizerResult
import re

# 사업자등록번호 (10자리)
class KRBusinessRegistrationRecognizer(EntityRecognizer):
    """
    사업자등록번호 인식기:

    정책:
    - 10자리 숫자: 220-81-62517, 2208162517

    검증:
    - 국세청 가중치 [1,3,7,1,3,7,1,3,5]
    - tens(d9*5) 더하기
    - 마지막 자릿수 비교
    """
    def __init__(self):
        super().__init__(supported_entities=["KR_BUSINESS_NO"], supported_language="en")
        self.candidate = re.compile(r"(?<!\d)(\d{3})-?(\d{2})-?(\d{5})(?!\d)")
        self.ctx = re.compile(r"(사업자(?:등록)?|사업자번호|사업자등록증|사업자등록번호)", re.IGNORECASE)

    @staticmethod
    def _digits(*parts: str) -> str:
        s = "".join(parts)
        return re.sub(r"\D", "", s)

    @staticmethod
    def _looks_bad(d: str) -> bool:
        return (len(set(d)) == 1) or (d == "0"*10)

    @staticmethod
    def _checksum_ok(d: str) -> bool:
        if len(d) != 10 or not d.isdigit():
            return False
        nums = [int(c) for c in d]
        w = [1,3,7,1,3,7,1,3,5]
        s = sum(n*w[i] for i, n in enumerate(nums[:9]))
        s += (nums[8] * 5) // 10
        check = (10 - (s % 10)) % 10
        return check == nums[9]

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "KR_BUSINESS_NO" not in entities or not text:
            return []

        results: List[RecognizerResult] = []
        for m in self.candidate.finditer(text):
            d = self._digits(*m.groups())
            if self._looks_bad(d):
                continue
            if not self._checksum_ok(d):
                continue

            score = 0.90
            L = max(0, m.start() - 24); R = min(len(text), m.end() + 24)
            if self.ctx.search(text[L:R]):
                score = min(0.98, score + 0.06)

            results.append(RecognizerResult("KR_BUSINESS_NO", m.start(), m.end(), score))
        return results