import re


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
