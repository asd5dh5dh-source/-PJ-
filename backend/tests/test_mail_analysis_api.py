from datetime import date

from fastapi.testclient import TestClient

from app.main import create_app


class ArchiveRepository:
    def list_candidates(self, filters=None, **filter_values):
        assert filters == {"final_status": "closed"}
        return [
            {
                "case_id": "COM-001",
                "customer_name": "Example Materials",
                "customer_request": "Investigate gas generation",
                "original_mail_body": "Gas generation was reported.",
                "voc_type": "Inquiry",
                "voc_subtype": "Gas Generation",
                "product_equipment": "NCA",
                "priority": "High",
                "responsible_departments": "Quality, Engineering",
                "final_status": "closed",
                "record_origin": "historical",
                "received_at": date(2026, 1, 1),
            }
        ]

    def get(self, case_id):
        return None


class CollaborationRepository:
    def dashboard(self, date_from, date_to):
        return {"stage_counts": [], "due_tasks": [], "recent_requests": []}

    def list_notifications(self):
        return []

    def list_daily_notification_task_ids(self):
        return []


def test_mail_analysis_extracts_sender_and_returns_closed_bm25_cases():
    client = TestClient(create_app(ArchiveRepository(), collaboration_repository=CollaborationRepository()))

    response = client.post(
        "/api/mail-analysis",
        json={"original_mail_body": "From: Jane Doe <jane@example.com>\nCompany: Example Materials\n\nPlease investigate gas generation."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sender_name"] == "Jane Doe"
    assert payload["sender_email"] == "jane@example.com"
    assert payload["sender_company"] == "Example Materials"
    assert payload["extracted_keywords"] == ["investigate", "gas", "generation"]
    assert payload["suggested_customer_request"] == "Please investigate gas generation."
    assert payload["suggested_product_equipment"] == "NCA"
    assert payload["suggested_priority"] == "high"
    assert payload["suggested_departments"] == ["Quality", "Engineering"]
    assert payload["items"][0]["case_id"] == "COM-001"
    assert payload["items"][0]["final_score"] > payload["items"][0]["bm25_score"]


def test_mail_analysis_extracts_company_and_request_only_from_korean_mail_body():
    client = TestClient(create_app(ArchiveRepository(), collaboration_repository=CollaborationRepository()))

    response = client.post(
        "/api/mail-analysis",
        json={"original_mail_body": "\uc548\ub155\ud558\uc138\uc694. Example Materials \ud488\uc9c8\ud300 \uae40\ucca0\uc218 \ub2f4\ub2f9\uc790\uc785\ub2c8\ub2e4.\n\ucd5c\uadfc \ubcf4\uad00 \uc911 \uac00\uc2a4 \ubc1c\uc0dd \uac00\ub2a5\uc131\uc774 \ud655\uc778\ub418\uc5b4 \ub0b4\ubd80 \uac80\ud1a0 \uc911\uc785\ub2c8\ub2e4.\n\uc6d0\uc778 \ubd84\uc11d \uacb0\uacfc\uc640 \ucd9c\ud558 \uac00\ub2a5 \uc77c\uc815\uc744 \ud68c\uc2e0\ud574 \uc8fc\uc2ed\uc2dc\uc624."},
    )

    payload = response.json()
    assert payload["sender_company"] == "Example Materials"
    assert payload["suggested_customer_request"] == "\uc6d0\uc778 \ubd84\uc11d \uacb0\uacfc\uc640 \ucd9c\ud558 \uac00\ub2a5 \uc77c\uc815\uc744 \ud68c\uc2e0\ud574 \uc8fc\uc2ed\uc2dc\uc624."


def test_mail_analysis_marks_no_history_when_no_keyword_matches_a_closed_case():
    client = TestClient(create_app(ArchiveRepository(), collaboration_repository=CollaborationRepository()))

    response = client.post(
        "/api/mail-analysis",
        json={"original_mail_body": "Superconducting quantum flux instability was observed."},
    )

    payload = response.json()
    assert payload["suggested_voc_subtype"] == "\uacfc\uac70 \uc774\ub825 \uc5c6\uc74c"
    assert payload["items"] == []
