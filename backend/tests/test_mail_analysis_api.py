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
    assert payload["items"][0]["case_id"] == "COM-001"
    assert payload["items"][0]["final_score"] > payload["items"][0]["bm25_score"]
