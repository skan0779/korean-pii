# - 사업자등록번호: 10자리 (중복 o)
# - 전화번호: 11자리 (중복 o)

from typing import List, Tuple, Dict
from presidio_analyzer import EntityRecognizer, RecognizerResult
import re

# 은행계좌 (7~14자리 숫자)
class KRBankAccountRecognizer(EntityRecognizer):
    """
    계좌번호 인식기:
    - 각 은행 별 정규식
    - 각 은행 별 문맥 키워드
    """
    def __init__(self, bank_specs: List[Dict]):
        super().__init__(supported_entities=["KR_BANK_ACCOUNT"], supported_language="en")
        self.patterns: List[Tuple[re.Pattern, re.Pattern]] = []
        for spec in bank_specs:
            ctx_words = spec.get("context", [])
            ctx_re = self._compile_context(ctx_words) if ctx_words else None
            for key in ("modern", "legacy"):
                for rx in spec.get(key, []):
                    pat = re.compile(rx)
                    self.patterns.append((pat, ctx_re))

    @staticmethod
    def _compile_context(words: List[str]) -> re.Pattern:
        if not words:
            return re.compile(r"$^")
        return re.compile("|".join(map(re.escape, words)), re.IGNORECASE)

    @staticmethod
    def _digits(s: str) -> str:
        return re.sub(r"\D", "", s)

    @staticmethod
    def _has_ctx(text: str, span: Tuple[int, int], ctx_re: re.Pattern) -> bool:
        if ctx_re is None:
            return False
        L = max(0, span[0] - 32); R = min(len(text), span[1] + 32)
        return bool(ctx_re.search(text[L:R]))

    def _emit(self, bucket: List[RecognizerResult], start: int, end: int, base: float, ctx: bool):
        score = min(0.90, base + (0.15 if ctx else 0.0))
        bucket.append(RecognizerResult("KR_BANK_ACCOUNT", start, end, score))

    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        if "KR_BANK_ACCOUNT" not in entities or not text:
            return []

        out: List[RecognizerResult] = []
        seen = set()

        def scan(pat: re.Pattern, ctx_re: re.Pattern, base: float = 0.75):
            for m in pat.finditer(text):
                s, e = m.start(), m.end()
                if (s, e) in seen:
                    continue
                seen.add((s, e))
                self._emit(out, s, e, base, self._has_ctx(text, (s, e), ctx_re))

        for pat, ctx_re in self.patterns:
            scan(pat, ctx_re, base=0.75)

        return out

# 한국산업은행(KDB)
def kdb_spec() -> Dict:
    yyy_modern = "(?:013|020|019|011|022)"
    yy_legacy = "(?:13|20|19|11|22)"
    modern = [
        # 14자리: YYY-ZZZZZZZC-XXX 
        rf"(?<!\d){yyy_modern}-\d{{8}}-\d{{3}}(?!\d)",
        rf"(?<!\d){yyy_modern}\ \d{{8}}\ \d{{3}}(?!\d)",
        rf"(?<!\d){yyy_modern}\d{{11}}(?!\d)",
    ]
    legacy = [
        # 11자리: XXX-YY-ZZZZZC
        rf"(?<!\d)\d{{3}}-{yy_legacy}-\d{{6}}(?!\d)", 
        rf"(?<!\d)\d{{3}}\ {yy_legacy}\ \d{{6}}(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_legacy}\d{{6}}(?!\d)",
    ]
    return {
        "bank": "KDB",
        "context": ["한국산업은행","KDB산업은행","산업은행"],
        "modern": modern,
        "legacy": legacy,
    }

# 기업은행(IBK)
def ibk_spec() -> Dict:
    yy_modern = "(?:01|02|03|13|07|06|04)"
    modern = [
        # 12자리: XXX-YY-ZZZZZZC
        rf"(?<!\d)\d{{3}}-{yy_modern}-\d{{6}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_modern}\ \d{{6}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_modern}\d{{7}}(?!\d)",
        # 14자리: XXX-BBBBBB-YY-ZZC
        rf"(?<!\d)\d{{3}}-\d{{6}}-{yy_modern}-\d{{2}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ \d{{6}}\ {yy_modern}\ \d{{2}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\d{{6}}{yy_modern}\d{{3}}(?!\d)",
    ]
    legacy = []
    return {
        "bank": "IBK",
        "context": ["기업은행","IBK기업은행","중소기업은행"],
        "modern": modern,
        "legacy": legacy
    }

# 국민은행(KB)
def kb_spec() -> dict:
    yy_modern = r"(?:01|02|21|24|05|04|25|26)"
    yy_legacy = r"(?:01|02|25|06|18|37|90)" 
    modern = [
        # 14자리: AAAAYY-ZZ-ZZZZZC
        rf"(?<!\d)\d{{4}}{yy_modern}-\d{{2}}-\d{{6}}(?!\d)",
        rf"(?<!\d)\d{{4}}\ {yy_modern}\ \d{{2}}\ \d{{6}}(?!\d)",
        rf"(?<!\d)\d{{4}}{yy_modern}\d{{8}}(?!\d)", 
    ]
    legacy = [
        # 12자리: XXXX-YY-ZZZZZC
        rf"(?<!\d)\d{{4}}-{yy_legacy}-\d{{6}}(?!\d)",
        rf"(?<!\d)\d{{4}}\ {yy_legacy}\ \d{{6}}(?!\d)",
        rf"(?<!\d)\d{{4}}{yy_legacy}\d{{6}}(?!\d)",
        # 14자리: XXXX-YY-ZZZZZZZC
        rf"(?<!\d)\d{{4}}-{yy_legacy}-\d{{8}}(?!\d)",
        rf"(?<!\d)\d{{4}}\ {yy_legacy}\ \d{{8}}(?!\d)",
        rf"(?<!\d)\d{{4}}{yy_legacy}\d{{8}}(?!\d)",
    ]
    return {
        "bank": "KB",
        "context": ["KB국민은행", "국민은행", "KB국민"],
        "modern": modern,
        "legacy": legacy,
    }

# 수협은행(SH)
def sh_spec() -> dict:
    yyy_modern = r"(?:101|201|102|202|209|103|208|106|108|113|114|206)" 
    yy_legacy = r"(?:01|02|06|08)"          
    yy_modern = r"40"          
    modern = [
        # 12자리: YYYZ-ZZZZ-ZZZC
        rf"(?<!\d){yyy_modern}\d-\d{{4}}-\d{{3}}\d(?!\d)",
        rf"(?<!\d){yyy_modern}\d\ \d{{4}}\ \d{{3}}\d(?!\d)",
        rf"(?<!\d){yyy_modern}\d\d{{8}}(?!\d)",
        # 14자리: XXX-YY-ZZZZZZZZ-C
        rf"(?<!\d)\d{{3}}-{yy_modern}-\d{{8}}-\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_modern}\ \d{{8}}\ \d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_modern}\d{{9}}(?!\d)",
    ]
    legacy = [
        # 11자리: XXX-YY-ZZZZZ-C
        rf"(?<!\d)\d{{3}}-{yy_legacy}-\d{{5}}-\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_legacy}\ \d{{5}}\ \d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_legacy}\d{{6}}(?!\d)",
    ]
    return {
        "bank": "SH",
        "context": ["SH수협은행", "수협은행", "수협", "SH수협"],
        "modern": modern,
        "legacy": legacy,
    }

# 농협은행(NH) XX
def nh_spec() -> dict:
    # 기본 과목코드
    nh_bank = ["01","02","12","06","05","17"]
    unit_nh = ["51","52","56","55"]
    # 가상계좌 코드
    va_2 = ["64","65","66","67"]
    va_3 = ["790","791","792"]
    # 적금/신탁
    dep_nh   = ["04","10","14","21","24","34","45","47","49","59","80"]
    dep_unit = ["54","60","84","94","98"]
    trust    = ["28","31","43","46","79","81","86","87","88"]
    yyy_13 = (
        "3(?:" + "|".join(nh_bank + unit_nh + dep_nh + dep_unit) + ")"
        + "|0(?:" + "|".join(trust) + ")"
    )
    yyy_13 = f"(?:{yyy_13})"
    # 2자리/3자리 가상계좌 코드
    ay2  = "(?:" + "|".join(va_2) + ")"
    ay3  = "(?:" + "|".join(va_3) + ")"
    yy_legacy = "(?:" + "|".join(nh_bank + unit_nh) + ")"
    modern = [
        # 현행 13자리: YYY-ZZZZ-ZZZZ-CT  (3-4-4-2)
        rf"(?<!\d){yyy_13}-\d{{4}}-\d{{4}}-\d{{2}}(?!\d)", 
        rf"(?<!\d){yyy_13}\ \d{{4}}\ \d{{4}}\ \d{{2}}(?!\d)",
        rf"(?<!\d){yyy_13}\d{{10}}(?!\d)",
        # 현행 가상계좌(14자리): AYY-ZZZZ-ZZZZ-ZZC (3-4-4-3)
        rf"(?<!\d){ay3}-\d{{4}}-\d{{4}}-\d{{3}}(?!\d)",
        rf"(?<!\d){ay3}\ \d{{4}}\ \d{{4}}\ \d{{3}}(?!\d)",
        rf"(?<!\d){ay3}\d{{11}}(?!\d)",
        # 현행 가상계좌(13자리 변형 허용): YY-ZZZZ-ZZZZ-ZZC
        rf"(?<!\d){ay2}-\d{{4}}-\d{{4}}-\d{{3}}(?!\d)",
        rf"(?<!\d){ay2}\ \d{{4}}\ \d{{4}}\ \d{{3}}(?!\d)",
        rf"(?<!\d){ay2}\d{{11}}(?!\d)",
    ]
    legacy = [
        # 구계좌 NH농협은행: XXX(X)-YY-ZZZZZC → 11/12자리 (3~4 - 2 - 6)
        rf"(?<!\d)\d{{3,4}}-{yy_legacy}-\d{{5}}\d(?!\d)",     
        rf"(?<!\d)\d{{3,4}}\ {yy_legacy}\ \d{{5}}\d(?!\d)",   
        rf"(?<!\d)\d{{3,4}}{yy_legacy}\d{{6}}(?!\d)",          
        # 구계좌 농업협동조합: XXXXXX-YY-ZZZZZC → 14자리 (6 - 2 - 6)
        rf"(?<!\d)\d{{6}}-{yy_legacy}-\d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{6}}\ {yy_legacy}\ \d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{6}}{yy_legacy}\d{{6}}(?!\d)",
        # 구 가상계좌(14자리): BBBBBB-YY-ZZZZZC (6 - 2 - 6)
        rf"(?<!\d)\d{{6}}-{ay2}-\d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{6}}\ {ay2}\ \d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{6}}{ay2}\d{{6}}(?!\d)",
    ]
    return {
        "bank": "NH",
        "context": ["NH농협은행","농협은행","NH농협","농협","NH"],
        "modern": modern,
        "legacy": legacy
    }

# 우리은행(WOORI)
def woori_spec() -> dict:
    syyy_modern  = r"(?:1002|1003|1004|1005|1006|1007)"
    yy_modern = r"(?:18|92)"
    modern = [
        # 13자리: SYYY-CZZ-ZZZZZZ
        rf"(?<!\d){syyy_modern}-\d{{3}}-\d{{6}}(?!\d)",
        rf"(?<!\d){syyy_modern}\ \d{{3}}\ \d{{6}}(?!\d)",  
        rf"(?<!\d){syyy_modern}\d{{9}}(?!\d)",  
        # 14자리: XXX-BBBBBC-YY-ZZC  
        rf"(?<!\d)\d{{3}}-\d{{6}}-{yy_modern}-\d{{2}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ \d{{6}}\ {yy_modern}\ \d{{2}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\d{{6}}{yy_modern}\d{{3}}(?!\d)",
    ]
    legacy = []
    return {
        "bank": "WOORI",
        "context": ["우리은행", "우리"],
        "modern": modern,
        "legacy": legacy
    }

# 제일은행(SC)
def sc_spec() -> dict:
    yy_modern = r"(?:10|20|30|85)"
    yy_va = r"(?:15|16)"
    modern = [
        # 11자리: XXX-YY-ZZZZZC
        rf"(?<!\d)\d{{3}}-{yy_modern}-\d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_modern}\ \d{{5}}\d(?!\d)",  
        rf"(?<!\d)\d{{3}}{yy_modern}\d{{6}}(?!\d)",   
        # 14자리: XXX-YY-ZZZZZZZZC
        rf"(?<!\d)\d{{3}}-{yy_va}-\d{{8}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_va}\ \d{{8}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_va}\d{{9}}(?!\d)",       
    ]
    legacy = []
    return {
        "bank": "SC",
        "context": ["SC제일은행", "제일은행", "SC"],
        "modern": modern,
        "legacy": legacy
    }

# 한국씨티은행(CITI)
def citi_spec() -> dict:
    syyy_modern = r"(?:1002|1003|1004|1005|1006|1007)"
    yy_modern = r"(?:25|41|24|18)"
    modern = [
        # 13자리: SYYY-CZZ-ZZZZZZ
        rf"(?<!\d){syyy_modern}-\d{{3}}-\d{{6}}(?!\d)",
        rf"(?<!\d){syyy_modern}\ \d{{3}}\ \d{{6}}(?!\d)",   
        rf"(?<!\d){syyy_modern}\d{{9}}(?!\d)",
        # 12자리: T-BBBBBB-CYY-ZZ           
        rf"(?<!\d)\d-\d{{6}}-\d{yy_modern}-\d{{2}}(?!\d)",
        rf"(?<!\d)\d\ \d{{6}}\ \d{yy_modern}\ \d{{2}}(?!\d)",
        rf"(?<!\d)\d\d{{6}}\d{yy_modern}\d{{2}}(?!\d)",
    ]
    return {
        "bank": "CITI",
        "context": ["한국씨티은행", "씨티은행","씨티"],
        "modern": modern,
        "legacy": []
    }

# 아이엠뱅크(IM)
def im_spec() -> dict:
    yyy_modern = r"(?:505|508|502|501|504|519|520|521|524|525|527|528|937)"
    modern = [
        # 12자리: YYY-ZZ-ZZZZZZ-C
        rf"(?<!\d){yyy_modern}-\d{{2}}-\d{{6}}-\d(?!\d)",   
        rf"(?<!\d){yyy_modern}\ \d{{2}}\ \d{{6}}\ \d(?!\d)",  
        rf"(?<!\d){yyy_modern}\d{{9}}(?!\d)",                
    ]

    return {
        "bank": "IM",
        "context": ["IM뱅크", "아이엠뱅크", "대구은행"],
        "modern": modern,
        "legacy": []
    }

# 부산은행(BNK)
def bnk_spec() -> dict:
    yyy_modern = r"(?:101|102|112|103|109|113)"
    yy_legacy  = r"(?:01|02|12|03|09|13|11)"
    modern = [
        # 13자리: YYY-ZZZZ-ZZZZ-ZC 
        rf"(?<!\d){yyy_modern}-\d{{4}}-\d{{4}}-\d{{2}}(?!\d)",
        rf"(?<!\d){yyy_modern}\ \d{{4}}\ \d{{4}}\ \d{{2}}(?!\d)", 
        rf"(?<!\d){yyy_modern}\d{{10}}(?!\d)",           
    ]
    legacy = [
        # 12자리: XXX-YY-ZZZZZZC
        rf"(?<!\d)\d{{3}}-{yy_legacy}-\d{{6}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_legacy}\ \d{{6}}\d(?!\d)",  
        rf"(?<!\d)\d{{3}}{yy_legacy}\d{{7}}(?!\d)",     
    ]
    return {
        "bank": "BNK",
        "context": ["BNK부산은행", "부산은행", "BNK부산", "BNK"],
        "modern": modern,
        "legacy": legacy
    }

# 11.광주은행(KJ) XX
def kj_spec() -> dict:
    yyy_mod = r"(?:107|108|109|121|123|124|122|103|101|127|716|731)"
    yyy_legacy = r"(?:107|109|121|103|101|127|731)"      
    modern = [
        rf"(?<!\d)\d{yyy_mod}-\d{{3}}-\d{{5}}\d(?!\d)",     # ZYYY-ZZZ-ZZZZZC (13)
        rf"(?<!\d)\d{yyy_mod}\ \d{{3}}\ \d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{yyy_mod}\d{{9}}(?!\d)",
    ]
    legacy = [
        rf"(?<!\d)\d{{3}}-{yyy_legacy}-\d{{5}}\d(?!\d)",    # XXX-YYY-ZZZZZC (12)
        rf"(?<!\d)\d{{3}}\ {yyy_legacy}\ \d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}{yyy_legacy}\d{{6}}(?!\d)",
    ]
    return {
        "bank": "KJ",
        "context": ["광주은행", "KJ은행", "광주", "KJ"],
        "modern": modern,
        "legacy": legacy
    }

# 12.제주은행(JEJU)
def jeju_spec() -> dict:
    yyy = r"(?:70[0-6]|70[7-9]|71[1-4]|769|77[0-9])"
    yy_legacy = r"(?:01|02|03|04|05|13)"
    modern = [
        rf"(?<!\d){yyy}-\d{{3}}-\d{{5}}\d(?!\d)",      # YYY-ZZZ-ZZZZZC (12자리)
        rf"(?<!\d){yyy}\ \d{{3}}\ \d{{5}}\d(?!\d)",   
        rf"(?<!\d){yyy}\d{{9}}(?!\d)",             
    ]
    legacy = [
        rf"(?<!\d)\d{{2}}-{yy_legacy}-\d{{5}}\d(?!\d)",    # XX-YY-ZZZZZC (10자리)
        rf"(?<!\d)\d{{2}}\ {yy_legacy}\ \d{{5}}\d(?!\d)", 
        rf"(?<!\d)\d{{2}}{yy_legacy}\d{{6}}(?!\d)",    
    ]
    return {
        "bank": "JEJU",
        "context": ["제주은행","JEJU BANK", "JEJU"],
        "modern": modern,
        "legacy": legacy
    }

# 13.새마을금고(MG)
def mg_spec() -> dict:
    yyy_cur = r"(?:00[2-5]|072|09[0-3]|200|202|205|20[7-9]|210|212)" 
    yy2_legacy = r"(?:09|10|13|37)"                               
    yy3_legacy = r"(?:80[1-9]|810|85[1-9]|860)"                    
    modern = [
        rf"(?<!\d)9{yyy_cur}-\d{{4}}-\d{{4}}-\d(?!\d)",
        rf"(?<!\d)9{yyy_cur}\ \d{{4}}\ \d{{4}}\ \d(?!\d)",
        rf"(?<!\d)9{yyy_cur}\d{{9}}(?!\d)",
    ]
    legacy = [
        rf"(?<!\d)\d{{4}}-{yy2_legacy}-\d{{6}}-\d(?!\d)",       # 구 13자리(2자리 코드)
        rf"(?<!\d)\d{{4}}\ {yy2_legacy}\ \d{{6}}\ \d(?!\d)",
        rf"(?<!\d)\d{{4}}{yy2_legacy}\d{{7}}(?!\d)",
        rf"(?<!\d)\d{{4}}-{yy3_legacy}-\d{{6}}-\d(?!\d)",       # 구 14자리(3자리 코드)
        rf"(?<!\d)\d{{4}}\ {yy3_legacy}\ \d{{6}}\ \d(?!\d)",
        rf"(?<!\d)\d{{4}}{yy3_legacy}\d{{7}}(?!\d)",
    ]
    return {
        "bank": "MG",
        "context": ["새마을금고", "MG새마을금고", "MG"],
        "modern": modern,
        "legacy": legacy
    }

# 14.신용협동조합(CU)
def cu_spec() -> dict:
    yyy = r"(?:110|131|132|133|134|135|136|137|138|142|170|171|172|173|174|177|178|185|186|731|910)"
    yy_legacy = r"(?:12|13)"
    modern = [
        rf"(?<!\d){yyy}-\d{{3}}-\d{{5}}\d(?!\d)",
        rf"(?<!\d){yyy}\ \d{{3}}\ \d{{5}}\d(?!\d)",
        rf"(?<!\d){yyy}\d{{9}}(?!\d)",
    ]
    legacy = [
        rf"(?<!\d)\d{{5}}-{yy_legacy}-\d{{5}}-\d(?!\d)",
        rf"(?<!\d)\d{{5}}\ {yy_legacy}\ \d{{5}}\ \d(?!\d)",
        rf"(?<!\d)\d{{5}}{yy_legacy}\d{{6}}(?!\d)",
    ]
    return {
        "bank": "CU",
        "context": ["신용협동조합", "신협", "CU"],
        "modern": modern,
        "legacy": legacy
    }

# 15.상호저축은행(MS)
def ms_spec() -> dict:
    yy = r"(?:13|21|22|23)"
    modern = [
        rf"(?<!\d)\d{{3}}-\d{{2}}-{yy}-\d{{6}}\d(?!\d)",      # WWW-XX-YY-ZZZZZZC
        rf"(?<!\d)\d{{3}}\ \d{{2}}\ {yy}\ \d{{6}}\d(?!\d)",  
        rf"(?<!\d)\d{{3}}\d{{2}}{yy}\d{{7}}(?!\d)",         
    ]
    legacy = [
        rf"(?<!\d)\d{{3}}-\d{{2}}-{yy}-\d{{3}}\d(?!\d)",       # WWW-XX-YY-ZZZC
        rf"(?<!\d)\d{{3}}\ \d{{2}}\ {yy}\ \d{{3}}\d(?!\d)",  
        rf"(?<!\d)\d{{3}}\d{{2}}{yy}\d{{4}}(?!\d)",   
    ]
    return {
        "bank": "MS",
        "context": ["상호저축은행", "저축은행", "SBI저축은행", "OK저축은행", "웰컴저축은행"],
        "modern": modern,
        "legacy": legacy
    }

# 16.산림조합(SJ)
def sj_spec() -> dict:
    yy13 = r"(?:21|22|30|27|32)"                     # 현행 13자리 YY (보통/자립/자유저축/기업자유)
    yy12 = r"(?:11|12|13|14|15)"                     # 현행 12자리 YY
    yy_legacy = r"(?:11|12|13|14|15|21|22|27|30|32)" # 구계좌 YY (자료 부재로 현행 코드 합집합 사용)
    modern = [
        # 13자리: ZZZZZ-YY-ZZZZZZ  (5-2-6)
        rf"(?<!\d)\d{{5}}-{yy13}-\d{{6}}(?!\d)",
        rf"(?<!\d)\d{{5}}\ {yy13}\ \d{{6}}(?!\d)",
        rf"(?<!\d)\d{{5}}{yy13}\d{{6}}(?!\d)",
        # 12자리: XXX-YY-ZZZZZZC  (3-2-7)
        rf"(?<!\d)\d{{3}}-{yy12}-\d{{6}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy12}\ \d{{6}}\ \d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy12}\d{{7}}(?!\d)",
    ]
    legacy = [
        # 11자리: XXX-YY-ZZZZZC  (3-2-6)
        rf"(?<!\d)\d{{3}}-{yy_legacy}-\d{{5}}\d(?!\d)",
        rf"(?<!\d)\d{{3}}\ {yy_legacy}\ \d{{5}}\ \d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_legacy}\d{{6}}(?!\d)",
    ]

    return {
        "bank": "SJ",
        "context": ["산림조합", "산림조합중앙회", "SJ산림조합", "SJ"],
        "modern": modern,
        "legacy": legacy
    }

# 18.하나은행(KEB)
def keb_spec() -> dict:
    yy = r"(?:01|02|04|05|07|08|32|37|38|60|94)"
    modern = [
        rf"(?<!\d)\d{{3}}-\d{{6}}-\d{{2}}\d{yy}(?!\d)",     # XXX-ZZZZZZ-ZZCYY (하이픈)
        rf"(?<!\d)\d{{3}}\ \d{{6}}\ \d{{2}}\d{yy}(?!\d)", 
        rf"(?<!\d)\d{{3}}\d{{6}}\d{{2}}\d{yy}(?!\d)",  
    ]
    return {
        "bank": "KEB",
        "context": ["하나은행", "KEB하나은행","KEB하나", "하나","KEB"],
        "modern": modern,
        "legacy": []
    }

# 19.신한은행(SOL)
def sol_spec() -> dict:
    syyy = r"(?:10\d|11\d|12\d|13\d|14\d|15\d|16[01]|180|298|268|269)"
    yyy_va = r"(?:560|561|562)"
    yy_legacy = r"(?:01|02|03|04|05|06|07|08|09|11|12|13|61)"
    yyy_sh_va = r"(?:099|901)"
    yy_ch_va = r"(?:81|82)"
    modern = [
        rf"(?<!\d){syyy}-\d{{3}}-\d{{5}}\d(?!\d)",      # YYY-ZZZ-ZZZZZC (12)
        rf"(?<!\d){syyy}\ \d{{3}}\ \d{{5}}\d(?!\d)", 
        rf"(?<!\d){syyy}\d{{9}}(?!\d)",  
        rf"(?<!\d){yyy_va}-\d{{3}}-\d{{8}}(?!\d)",      # YYY-TTT-ZZZZZZZC (14)
        rf"(?<!\d){yyy_va}\ \d{{3}}\ \d{{8}}(?!\d)",  
        rf"(?<!\d){yyy_va}\d{{11}}(?!\d)",            
    ]
    legacy = [
        rf"(?<!\d)\d{{3}}-{yy_legacy}-\d{{5}}\d(?!\d)",    # XXX-YY-ZZZZZC (11)
        rf"(?<!\d)\d{{3}}\ {yy_legacy}\ \d{{5}}\ \d(?!\d)",
        rf"(?<!\d)\d{{3}}{yy_legacy}\d{{6}}(?!\d)",  
        rf"(?<!\d)\d{{3}}-{yy_ch_va}-\d{{8}}(?!\d)",      # XXX-YY-ZZZZZZZC (13)
        rf"(?<!\d)\d{{3}}\ {yy_ch_va}\ \d{{8}}(?!\d)",  
        rf"(?<!\d)\d{{3}}{yy_ch_va}\d{{8}}(?!\d)",     
        rf"(?<!\d)\d{{3}}-{yyy_sh_va}-\d{{8}}(?!\d)",     # XXX-YYY-ZZZZZZZC (14)
        rf"(?<!\d)\d{{3}}\ {yyy_sh_va}\ \d{{8}}(?!\d)",  
        rf"(?<!\d)\d{{3}}{yyy_sh_va}\d{{8}}(?!\d)",        
    ]
    return {
        "bank": "SOL",
        "context": ["신한은행", "Shinhan Bank", "신한", "SH","SOL"],
        "modern": modern,
        "legacy": legacy
    }

# 20.케이뱅크(KBANK)
def kbank_spec() -> dict:
    modern = [
        r"(?<!\d)(?:100-1\d{2}-\d{2}\d{4}|100-2\d{2}-\d{2}\d{4}|100-5\d{2}-\d{2}\d{4}|110-2\d{2}-\d{2}\d{4})(?!\d)",
        r"(?<!\d)(?:100\ 1\d{2}\ \d{2}\d{4}|100\ 2\d{2}\ \d{2}\d{4}|100\ 5\d{2}\ \d{2}\d{4}|110\ 2\d{2}\ \d{2}\d{4})(?!\d)", # YYY-YNN-NNZZZZ (12자리)
        r"(?<!\d)(?:1001\d{8}|1002\d{8}|1005\d{8}|1102\d{8})(?!\d)",

        # 비대면 실명인증 입금전용계좌: 9-NNNNNNNNN (10자리)
        r"(?<!\d)9-\d{9}(?!\d)",
        # r"(?<!\d)9\ \d{9}(?!\d)",
        # r"(?<!\d)9\d{9}(?!\d)",

        # 휴대폰번호 연결서비스: ZZ-AAA-BBBB-CCC (2-3-4-3)
        r"(?<!\d)\d{2}-\d{3}-\d{4}-\d{3}(?!\d)",
        # r"(?<!\d)\d{2}\ \d{3}\ \d{4}\ \d{3}(?!\d)",

        # 간편송금/안심계좌/신용카드결제 포인트구매: (7|9)-NNNN-NNN-NNNN
        r"(?<!\d)(?:7|9)-\d{4}-\d{3}-\d{4}(?!\d)",
        # r"(?<!\d)(?:7|9)\ \d{4}\ \d{3}\ \d{4}(?!\d)",
        # r"(?<!\d)(?:7|9)\d{11}(?!\d)",

        # 여신가상계좌: 여신계좌번호(12자리)-ZZ
        r"(?<!\d)\d{12}-\d{2}(?!\d)",
        # r"(?<!\d)\d{12}\ \d{2}(?!\d)",
        # r"(?<!\d)\d{14}(?!\d)",
    ]

    return {
        "bank": "KBANK",
        "context": ["케이뱅크", "K뱅크", "KBANK", "K Bank"],
        "modern": modern,
        "legacy": []
    }

# 21.카카오뱅크(KAKAO)
def kakao_spec() -> dict:
    prefix = r"(?:3333|3388|3355|3310|7777|7979|9101)"
    modern = [
        rf"(?<!\d){prefix}-\d{{2}}-\d{{7}}(?!\d)",
        rf"(?<!\d){prefix}\ \d{{2}}\ \d{{7}}(?!\d)",
        rf"(?<!\d){prefix}\d{{9}}(?!\d)",
    ]
    return {
        "bank": "KAKAO",
        "context": ["카카오뱅크", "KakaoBank", "KAKAO BANK"],
        "modern": modern,
        "legacy": []
    }

# 22.토스뱅크(TOSS)
def toss_spec() -> dict:
    yyy = r"(?:100|106|200|300|150|700|190)"
    va4 = r"(?:17|19)\d{2}"
    modern = [
        rf"(?<!\d){yyy}\d-\d{{4}}-\d{{3}}\d(?!\d)",     # YYYZ-ZZZZ-ZZZC (12자리)
        rf"(?<!\d){yyy}\d\ \d{{4}}\ \d{{3}}\d(?!\d)",
        rf"(?<!\d){yyy}\d\d{{8}}(?!\d)",   
        rf"(?<!\d){va4}-\d{{4}}-\d{{6}}(?!\d)",         # (17/19)ZZ-ZZZZ-ZZZZ (14자리)
        rf"(?<!\d){va4}\ \d{{4}}\ \d{{6}}(?!\d)",
        rf"(?<!\d){va4}\d{{10}}(?!\d)",
    ]
    return {
        "bank": "TOSS",
        "context": ["토스뱅크", "Toss Bank", "토스", "TOSS"],
        "modern": modern,
        "legacy": []
    }

BANK_SPECS: List[Dict] = [
    kdb_spec(),
    kb_spec(),
    sh_spec(),
    nh_spec(),
    woori_spec(),
    sc_spec(),
    citi_spec(),
    im_spec(),
    bnk_spec(),
    kj_spec(),
    jeju_spec(),
    mg_spec(),
    cu_spec(),
    ms_spec(),
    sj_spec(),
    keb_spec(),
    sol_spec(),
    kbank_spec(),
    kakao_spec(),
    toss_spec(),
]