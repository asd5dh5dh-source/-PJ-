from datetime import date

from fastapi.testclient import TestClient

from app.main import create_app
from app.routers import mail_analysis


class ArchiveRepository:
    def list_candidates(self, filters=None, **filter_values):
        cases = [
            {
                "case_id": "COM-001",
                "customer_name": "Example Materials",
                "customer_request": "Investigate gas generation. Impurity Control LFP lot containment root cause action",
                "original_mail_body": "Gas generation was reported. Impurity Control LFP lot containment root cause action was reported.",
                "voc_type": "Inquiry",
                "voc_subtype": "Gas Generation",
                "product_equipment": "NCA",
                "priority": "High",
                "responsible_departments": "Quality, Engineering",
                "final_status": "closed",
                "record_origin": "historical",
                "received_at": date(2026, 1, 1),
            },
            {
                "case_id": "COM-002",
                "customer_name": "Example Materials",
                "customer_request": "Investigate impurity control and lot performance deviation",
                "original_mail_body": "Impurity Control LFP lot containment and root cause review.",
                "voc_type": "Complaint",
                "voc_subtype": "Impurity Control",
                "product_equipment": "LFP",
                "priority": "High",
                "responsible_departments": "Quality",
                "final_status": "closed",
                "record_origin": "historical",
                "received_at": date(2026, 1, 2),
            },
            {
                "case_id": "COM-003",
                "customer_name": "Missbusy",
                "customer_request": "Investigate packing damage and containment action",
                "original_mail_body": "Packing Damage LFP lot containment action.",
                "voc_type": "Complaint",
                "voc_subtype": "Packing Damage",
                "product_equipment": "LFP",
                "priority": "High",
                "responsible_departments": "Quality",
                "final_status": "closed",
                "record_origin": "historical",
                "received_at": date(2026, 1, 3),
            },
        ]
        return [
            case for case in cases
            if all(str(case.get(key, "")).casefold() == str(value).casefold() for key, value in (filters or {}).items())
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


def test_mail_analysis_uses_explicit_mail_topic_before_a_keyword_nearest_subtype():
    client = TestClient(create_app(ArchiveRepository(), collaboration_repository=CollaborationRepository()))

    response = client.post(
        "/api/mail-analysis",
        json={"original_mail_body": """안녕하세요. 삼성SDI 수입품질 담당자입니다.

[문의/요청 주제: Impurity Control]
LFP Lot을 적용한 셀 평가에서 저전압 및 성능 편차가 확인되었습니다.
동일 Lot 영향 범위, 즉시 격리/출하보류 조치, 원인분석 및 재발방지 계획을 제출해 주십시오."""},
    )

    assert response.status_code == 200
    payload = response.json()
    assert mail_analysis._explicit_voc_subtype("[문의/요청 주제: Impurity Control]") == "Impurity Control"
    assert payload["suggested_voc_subtype"] == "Impurity Control"


def test_mail_analysis_extracts_japanese_sender_topic_and_product():
    client = TestClient(create_app(ArchiveRepository(), collaboration_repository=CollaborationRepository()))

    response = client.post(
        "/api/mail-analysis",
        json={"original_mail_body": """お世話になっております。Missbusyの受入品質担当、田中です。

件名：Packing Damage
納入されたLFP Lotを使用したセル評価で性能のばらつきが確認されました。
影響範囲、隔離・出荷保留の暫定措置、原因分析および再発防止計画をご提出ください。"""},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sender_name"] == "田中"
    assert payload["sender_company"] == "Missbusy"
    assert payload["suggested_voc_subtype"] == "Packing Damage"
    assert payload["suggested_product_equipment"] == "LFP"
