import re
import unicodedata

def normalize_title(title: str) -> str:
    if not title:
        return ""
    t = unicodedata.normalize('NFC', title)
    t = re.sub(r'[\x00-\x1F\x7F\u200B-\u200D\uFEFF]', '', t)
    t = t.strip()
    t = re.sub(r'\s+', ' ', t)
    return t.lower()
