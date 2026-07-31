import re

import langid


MALAY_MARKERS = {
    "apa",
    "awak",
    "bagaimana",
    "boleh",
    "dan",
    "dengan",
    "khabar",
    "saya",
    "selamat",
    "terima",
    "tidak",
    "tolong",
    "yang",
}
LANGUAGE_NAMES = {
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "id": "Indonesian",
    "ja": "Japanese",
    "ko": "Korean",
    "ms": "Malay",
    "pt": "Portuguese",
    "zh": "Chinese",
}


def detect_language(text: str, fallback: str = "en") -> str:
    normalized = text.strip()
    if not normalized:
        return fallback
    if re.search(r"[\u3040-\u30ff]", normalized):
        return "ja"
    if re.search(r"[\uac00-\ud7af]", normalized):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", normalized):
        return "zh"

    words = set(re.findall(r"[a-zA-ZÀ-ÿ]+", normalized.lower()))
    if len(words & MALAY_MARKERS) >= 2:
        return "ms"
    if len(normalized) < 4:
        return fallback

    language, _ = langid.classify(normalized)
    return language or fallback


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)
