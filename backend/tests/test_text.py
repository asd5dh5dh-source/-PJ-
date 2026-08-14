from app.services.text import normalize_text, tokenize


def test_normalize_text_removes_html_and_repeated_spaces():
    assert normalize_text("<p>Cell  Low</p>\nVoltage") == "cell low voltage"


def test_tokenize_accepts_empty_values():
    assert tokenize(None) == []
