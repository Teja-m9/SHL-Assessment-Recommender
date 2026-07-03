import re


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())