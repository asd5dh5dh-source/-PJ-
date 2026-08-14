import html
import re


def normalize_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^0-9A-Za-z\uac00-\ud7a3_+-]+", " ", text.lower())
    return " ".join(text.split())


def tokenize(value: str | None) -> list[str]:
    return normalize_text(value).split()
