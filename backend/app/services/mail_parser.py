from email.parser import Parser
from email.utils import parseaddr


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
    return {
        "sender_name": sender_name.strip() or None,
        "sender_email": sender_email.strip() or None,
        "sender_company": company,
    }
