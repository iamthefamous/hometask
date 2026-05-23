import re
import string


_SAFE_PUNCT_TABLE = str.maketrans("", "", string.punctuation)
_TOKEN_PATTERN = re.compile(r"^[A-Za-z][A-Za-z'`.-]*$")
_BANNED_SUBSTRINGS = (
    "view bio",
    "@",
    "http://",
    "https://",
    "signal",
    "email",
    "reporter at",
)
_LEADING_NAME_PATTERN = re.compile(r"^\s*([A-Z][A-Za-z'`.-]+)\s+([A-Z][A-Za-z'`.-]+)")
_ROLE_WORDS = {
    "editor",
    "manager",
    "reporter",
    "writer",
    "producer",
    "director",
    "analyst",
    "news",
    "audience",
    "development",
    "senior",
}


def normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = text.translate(_SAFE_PUNCT_TABLE)
    return re.sub(r"\s+", " ", text)


def is_probable_person_name(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _BANNED_SUBSTRINGS):
        return False
    if len(text) > 80:
        return False
    if text.count(",") > 1 or text.count(".") > 1:
        return False

    words = [word for word in re.split(r"\s+", text) if word]
    if len(words) < 2 or len(words) > 6:
        return False
    if len(words) <= 3 and all(word.lower() in _ROLE_WORDS for word in words):
        return False
    if not all(_TOKEN_PATTERN.match(word) for word in words):
        return False
    return True


def extract_canonical_person_name(value: str) -> str | None:
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return None
    words = [word for word in text.split(" ") if word]
    if len(words) > 2:
        match = _LEADING_NAME_PATTERN.match(text)
        if match:
            candidate = f"{match.group(1)} {match.group(2)}"
            if is_probable_person_name(candidate):
                return candidate

    if is_probable_person_name(text):
        return text
    return None
