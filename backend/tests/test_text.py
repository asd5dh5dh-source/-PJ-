from app.services.text import clean_customer_request, normalize_text, tokenize


def test_normalize_text_removes_html_and_repeated_spaces():
    assert normalize_text("<p>Cell  Low</p>\nVoltage") == "cell low voltage"


def test_tokenize_accepts_empty_values():
    assert tokenize(None) == []


def test_clean_customer_request_recovers_a_replacement_character_from_original_mail():
    original_mail = """안녕하세요. 고객사 담당자입니다.

LFP Lot 성능 편차를 검토하고 있습니다.
동일 Lot 영향 범위와 원인분석 및 재발방지 계획을 제출해 주십시오.
고객 최초 회신 요청 기한은 2026-07-23입니다."""

    assert clean_customer_request("양극재 ��성 검토가 필요합니다.", original_mail) == (
        "동일 Lot 영향 범위와 원인분석 및 재발방지 계획을 제출해 주십시오."
    )
