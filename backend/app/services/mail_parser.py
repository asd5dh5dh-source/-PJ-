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
        patterns = (
            r"(?:안녕하세요[,.!]?\s*)?"
            r"(?P<company>[A-Za-z0-9가-힣][A-Za-z0-9가-힣 .&()/-]{1,60}?)\s+"
            r"(?:[A-Za-z0-9가-힣]+(?:팀|부|실|그룹|센터))\s+"
            r"(?:[가-힣]{2,4}|[A-Za-z][A-Za-z .'-]{1,40})\s+"
            r"(?:담당자|책임자|매니저|manager)",
        )
        for pattern in patterns:
            match = re.search(pattern, raw_mail, re.I)
            if match:
                company = match.group("company").strip(" .,-")
                break
    if company is None:
        japanese_match = re.search(
            r"(?P<company>[A-Za-z0-9][A-Za-z0-9 .&()/-]{1,60}?)の[^、\n]{0,24}(?:担当|責任者)[、,]\s*(?P<name>[\u4e00-\u9fff々]{1,8})です",
            raw_mail,
        )
        if japanese_match:
            company = japanese_match.group("company").strip(" .,-")
            sender_name = sender_name or japanese_match.group("name")
    return {
        "sender_name": sender_name.strip() or None,
        "sender_email": sender_email.strip() or None,
        "sender_company": company,
    }
