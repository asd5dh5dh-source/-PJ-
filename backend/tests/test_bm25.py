import pytest

from app.services.bm25 import Bm25Index


@pytest.fixture
def candidates():
    return [
        {
            "case_id": "COM-001",
            "voc_subtype": "Cell Low Voltage",
            "customer_request": "Cell low voltage alarm",
            "original_mail_body": "The cell voltage is below the requested level.",
            "full_response_history": "Reviewed low voltage condition.",
        },
        {
            "case_id": "REQ-GAS-CONTENT-MATCH",
            "voc_subtype": "Gas Generation",
            "customer_request": "Gas generation is occurring during storage.",
            "original_mail_body": "Please investigate gas generation.",
            "full_response_history": "Gas generation containment was shared.",
        },
        {
            "case_id": "CUSTOMER-NAME-ONLY",
            "voc_subtype": "Other",
            "customer_name": "Gas Generation " * 100,
            "customer_request": "Need a shipping update.",
            "original_mail_body": "When will the shipment arrive?",
            "full_response_history": "Shipping team responded.",
        },
    ]


@pytest.fixture
def index():
    return Bm25Index()


def test_subtype_match_adds_exactly_ten_percent(index, candidates):
    ranked = index.rank("cell low voltage", candidates, "Cell Low Voltage", 3)

    matched = next(item for item in ranked if item.case_id == "COM-001")
    assert matched.final_score == pytest.approx(matched.bm25_score * 1.1)


def test_customer_name_does_not_override_stronger_request_match(index, candidates):
    ranked = index.rank("gas generation", candidates, "Gas Generation", 3)

    assert ranked[0].case_id == "REQ-GAS-CONTENT-MATCH"
    name_only = next(item for item in ranked if item.case_id == "CUSTOMER-NAME-ONLY")
    assert name_only.bm25_score == 0
    assert name_only.matched_keywords == []


def test_rank_reports_query_keywords_present_in_the_searchable_fields(index, candidates):
    ranked = index.rank("gas generation", candidates, "Other", 3)

    matched = next(item for item in ranked if item.case_id == "REQ-GAS-CONTENT-MATCH")
    assert matched.matched_keywords == ["gas", "generation"]


def test_repeated_terms_keep_scores_positive_and_subtype_boost_improves_rank(index):
    repeated_term_candidates = [
        {
            "case_id": "SUBTYPE-MATCH",
            "voc_subtype": "Gas Generation",
            "customer_request": "gas gas gas gas",
        },
        {
            "case_id": "OTHER-SUBTYPE",
            "voc_subtype": "Other",
            "customer_request": "gas gas gas gas",
        },
    ]

    ranked = index.rank(
        "gas",
        repeated_term_candidates,
        "Gas Generation",
        2,
    )

    assert all(item.bm25_score > 0 for item in ranked)
    assert ranked[0].case_id == "SUBTYPE-MATCH"
    assert ranked[0].final_score > ranked[1].final_score
