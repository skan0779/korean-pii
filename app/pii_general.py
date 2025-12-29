import yaml
import spacy
from pathlib import Path
from typing import List, Tuple, Dict
from app.recognizer.per_recognizer import KRPersonRecognizer
from app.recognizer.phone_recognizer import KRPhoneRecognizer
from app.recognizer.brn_recognizer import KRBusinessRegistrationRecognizer
from app.recognizer.ban_recognizer import KRBankAccountRecognizer, BANK_SPECS
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities.engine.recognizer_result import RecognizerResult

# Load YAML
ROOT = Path(__file__).resolve().parent
with open(ROOT/"combination.yml") as f:
    COMBOS = yaml.safe_load(f)

# NLP 엔진 설정 (SpaCy)
NLP = SpacyNlpEngine(models=[])
NLP.nlp = {"en": spacy.blank("en")}

# EMAIL_ADDRESS, CREDIT_CARD 내장 인식기 (Presidio)
REG = RecognizerRegistry()
REG.load_predefined_recognizers()

# PERSON 커스텀 인식기 (Leo97/KoELECTRA-small-v3-modu-ner)
REG.add_recognizer(KRPersonRecognizer())

# KR_PHONE_NUMBER 커스텀 인식기
REG.add_recognizer(KRPhoneRecognizer())

# KR_BANK_ACCOUNT 커스텀 인식기
REG.add_recognizer(KRBankAccountRecognizer(BANK_SPECS))

# KR_BUSINESS_NO 커스텀 인식기
REG.add_recognizer(KRBusinessRegistrationRecognizer())

# Anonymizer 설정
ANALYZER = AnalyzerEngine(nlp_engine=NLP, registry=REG)
ANON = AnonymizerEngine()

def pii_general(text: str) -> Tuple[bool, str, List[str]]:

    ents_en = ["EMAIL_ADDRESS", "CREDIT_CARD", "KR_PERSON", "KR_PHONE_NUMBER", "KR_BANK_ACCOUNT", "KR_BUSINESS_NO"]
    res = ANALYZER.analyze(text=text, language="en", entities=ents_en)
    anon_ready = [
        RecognizerResult(
            entity_type=r.entity_type,
            start=r.start,
            end=r.end,
            score=r.score,
        )
        for r in res
    ]

    print(res)
    if not res:
        return False, text, []

    by_type: Dict[str, List[tuple]] = {}
    for r in res:
        by_type.setdefault(r.entity_type, []).append((r.start, r.end))

    window = int(COMBOS["window"])
    involved = set()

    for a,b in COMBOS["and_rules"]:
        if a not in by_type or b not in by_type:
            continue
        if window==0:
            involved.update([a,b])
            continue
        if any(abs(sa-sb)<=window for sa,_ in by_type[a] for sb,_ in by_type[b]):
            involved.update([a,b])

    if not involved: 
        return False, text, []
    
    ops = {t: OperatorConfig("replace", {"new_value": COMBOS["tag_map"][t]}) for t in involved}
    masked_text = ANON.anonymize(text=text, analyzer_results=anon_ready, operators=ops).text
    labels = [COMBOS["label_map"][t] for t in COMBOS["label_map"] if t in involved]

    return True, masked_text, labels

