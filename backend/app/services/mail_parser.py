from email.parser import Parser
from email.utils import parseaddr
import re


def parse_sender(raw_mail: str) -> dict[str, str | None]:
    message = Parser().parsestr(raw_mail)
    sender_name, sender_email = parseaddr(message.get("from", ""))
    company = next(
        (
            message.get(header, "").strip()
            for header in ("company", "organization", "x-company")
            if message.get(header, "").strip()
        ),
        None,
    )
    if company is None:
        match = re.search(
            r"([A-Za-z][A-Za-z .&-]{1,60})\s+(?:[가-힣]+팀\s+)?[가-힣]{2,}\s+(?:담당자|책임자|manager)",
            raw_mail,
            re.I,
        )
        company = match.group(1).strip() if match else None
    return {
        "sender_name": sender_name.strip() or None,
        "sender_email": sender_email.strip() or None,
        "sender_company": company,
    }
