import html
import re


def normalize_text(value: str | None) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^0-9A-Za-z\uac00-\ud7a3_+-]+", " ", text.lower())
    return " ".join(text.split())


def tokenize(value: str | None) -> list[str]:
    return normalize_text(value).split()


def clean_customer_request(customer_request: str | None, original_mail_body: str | None) -> str | None:
    """Use the intact mail request sentence when an imported summary contains U+FFFD."""
    if not customer_request or "\ufffd" not in customer_request or not original_mail_body:
        return customer_request
    sentences = re.split(r"(?<=[.!?])\s*|\n+", original_mail_body)
    requested = [
        " ".join(sentence.split())
        for sentence in sentences
        if re.search(
            r"회신.*(?:해|바랍니다)|제출|확인.*(?:해|바랍니다)|검토.*(?:해|바랍니다)|조치.*(?:해|바랍니다)|제공.*(?:해|바랍니다)|please|request|provide|confirm|review|investigate",
            sentence,
            re.I,
        )
    ]
    return " ".join(requested).strip() or customer_request
