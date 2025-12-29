from typing import List, Tuple
from app.recognizer.rrn_recognizer import ResidentRegistrationRecognizer
from app.recognizer.arn_recognizer import AlienRegistrationRecognizer
from app.recognizer.dln_recognizer import DriverLicenseRecognizer
from app.recognizer.pn_recognizer import PassportRecognizer
from app.pii_general import pii_general

def pii_pipeline(text: str) -> Tuple[bool, str, List[str], str]:
    
    # 고유식별정보
    labels=[]
    blocked=False

    for fn in (
        ResidentRegistrationRecognizer,
        AlienRegistrationRecognizer,
        DriverLicenseRecognizer,
        PassportRecognizer
    ):
        hit, text, label = fn(text)
        if hit:
            labels += label
            blocked = True
    if blocked:
        return True, text, labels, "고유식별번호"

    # 일반개인정보
    blocked, text, label = pii_general(text)
    if blocked:
        return True, text, label, "일반개인정보"
    return False, text, [], ""