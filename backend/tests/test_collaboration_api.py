from copy import deepcopy
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


WRITER_HEADERS = {
    "X-Writer-Name": "Kim",
    "X-Writer-Password": "correct-password",
}


class AlwaysUnlockedWriterAttemptStore:
    def record_and_check_locked(self, writer_name, client_ip, succeeded):
        return False


class ArchiveRepository:
    def list_candidates(self, filters=None, **filter_values):
        return []

    def get(self, case_id):
        return None


class MemoryCollaborationRepository:
    def __init__(self):
        self.case = None
        self.next_task_id = 1
        self.audits = []

    def create_voc(self, values, tasks, writer_name, year):
        created_tasks = []
        for task in tasks:
            created_tasks.append({"id": self.next_task_id, "status": "not_started", **task})
            self.next_task_id += 1
        self.case = {
            **values,
            "id": 1,
            "case_id": f"VOC-{year}-0001",
            "round_number": 1,
            "stage": "received",
            "tasks": created_tasks,
            "reviews": [],
        }
        self.audits.append(("voc_request", self.case["case_id"], writer_name))
        return deepcopy(self.case)

    def create_round(self, case_id, values, writer_name):
        previous = self.case
        reopened = [
            {**task, "id": self.next_task_id + index, "status": "not_started"}
            for index, task in enumerate(previous["tasks"])
            if task["status"] != "excluded"
        ]
        self.next_task_id += len(reopened)
        self.case = {
            **previous,
            **values,
            "id": previous["id"] + 1,
            "round_number": previous["round_number"] + 1,
            "stage": "received",
            "tasks": reopened,
            "reviews": [],
        }
        self.audits.append(("voc_request", case_id, writer_name))
        return deepcopy(self.case)

    def get_case(self, case_id):
        if self.case is None or self.case["case_id"] != case_id:
            return None
        return {"case_id": case_id, "rounds": [deepcopy(self.case)], "audits": deepcopy(self.audits)}

    def get_task(self, task_id):
        if self.case is None:
            return None
        return next((task for task in self.case["tasks"] if task["id"] == task_id), None)

    def update_task(self, task_id, changes, writer_name):
        task = self.get_task(task_id)
        task.update(changes)
        self.audits.append(("department_task", str(task_id), writer_name))
        return deepcopy(task)

    def review_task(self, task_id, values, writer_name):
        review = {"id": len(self.case["reviews"]) + 1, "task_id": task_id, **values}
        self.case["reviews"].append(review)
        if values["decision"] == "rejected":
            self.get_task(task_id)["status"] = "reviewing"
        self.audits.append(("task_review", str(review["id"]), writer_name))
        return deepcopy(review)

    def approvals_complete(self, request_id):
        active = [task for task in self.case["tasks"] if task["status"] != "excluded"]
        manager_task_ids = {
            review["task_id"]
            for review in self.case["reviews"]
            if review["reviewer_role"] == "department_manager"
            and review["decision"] == "approved"
        }
        final_approved = any(
            review["reviewer_role"] == "final_approver"
            and review["decision"] == "approved"
            for review in self.case["reviews"]
        )
        return all(task["status"] == "completed" and task["id"] in manager_task_ids for task in active) and final_approved

    def change_stage(self, case_id, values, writer_name):
        self.case["stage"] = values["stage"]
        self.audits.append(("voc_stage", case_id, writer_name))
        return deepcopy(self.case)


@pytest.fixture(autouse=True)
def writer_environment(monkeypatch):
    monkeypatch.setenv(
        "VOC_WRITER_PASSWORD_HASH",
        "9246aa9be8de7b40d64eb664986430793b6cc13a19d2a456981e44f28303f9cf",
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def collaboration_repository():
    return MemoryCollaborationRepository()


@pytest.fixture
def client(collaboration_repository):
    app = create_app(
        ArchiveRepository(),
        receipt_date=lambda: date(2026, 8, 18),
        collaboration_repository=collaboration_repository,
    )
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()
    return TestClient(app)


VOC_PAYLOAD = {
    "customer_request": "Separator failure investigation",
    "original_mail_body": (
        "From: Jane Doe <jane@example.com>\n"
        "Company: Example Materials\n\nPlease investigate."
    ),
    "tasks": [{"department": "Quality", "due_date": "2026-08-20"}],
}


def test_voc_mutations_require_writer_headers(client):
    assert client.post("/api/voc", json=VOC_PAYLOAD).status_code == 401


def test_create_app_keeps_a_falsy_collaboration_repository():
    class FalsyRepository(MemoryCollaborationRepository):
        def __bool__(self):
            return False

    repository = FalsyRepository()
    app = create_app(
        ArchiveRepository(),
        receipt_date=lambda: date(2026, 8, 18),
        collaboration_repository=repository,
    )
    app.state.writer_attempt_store = AlwaysUnlockedWriterAttemptStore()

    response = TestClient(app).post(
        "/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD
    )

    assert response.status_code == 201
    assert repository.case is not None


def test_create_voc_issues_case_id_and_parses_sender_only(client):
    response = client.post("/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["case_id"] == "VOC-2026-0001"
    assert response.json()["sender_name"] == "Jane Doe"
    assert response.json()["sender_email"] == "jane@example.com"
    assert response.json()["sender_company"] == "Example Materials"
    assert response.json()["tasks"][0]["status"] == "not_started"


def test_follow_up_creates_second_round_and_reopens_prior_tasks(client):
    created = client.post("/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD).json()
    task_id = created["tasks"][0]["id"]
    completed = client.post(
        f"/api/tasks/{task_id}",
        headers=WRITER_HEADERS,
        json={
            "status": "completed",
            "response_content": "Corrective action complete",
            "due_date": "2026-08-20",
        },
    )
    assert completed.status_code == 200

    reply = client.post(
        f"/api/voc/{created['case_id']}/rounds",
        headers=WRITER_HEADERS,
        json={"customer_request": "additional question"},
    )

    assert reply.status_code == 201
    assert reply.json()["round_number"] == 2
    assert reply.json()["tasks"][0]["status"] == "not_started"


def test_customer_reply_requires_all_approvals(client):
    case_id = client.post("/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD).json()["case_id"]

    response = client.post(
        f"/api/voc/{case_id}/stage",
        headers=WRITER_HEADERS,
        json={"stage": "customer_reply"},
    )

    assert response.status_code == 409


def test_rejected_department_review_returns_task_to_reviewing(client):
    task_id = client.post("/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD).json()["tasks"][0]["id"]

    response = client.post(
        f"/api/tasks/{task_id}/review",
        headers=WRITER_HEADERS,
        json={
            "reviewer_role": "department_manager",
            "decision": "rejected",
            "comment": "More evidence required",
        },
    )

    assert response.status_code == 201
    detail = client.get("/api/voc/VOC-2026-0001").json()
    assert detail["rounds"][0]["tasks"][0]["status"] == "reviewing"


@pytest.mark.parametrize(
    ("stage", "reason_field"),
    [("cancelled", "cancellation_reason"), ("deleted", "deletion_reason")],
)
def test_terminal_stage_requires_reason(client, stage, reason_field):
    case_id = client.post("/api/voc", headers=WRITER_HEADERS, json=VOC_PAYLOAD).json()["case_id"]

    missing = client.post(
        f"/api/voc/{case_id}/stage",
        headers=WRITER_HEADERS,
        json={"stage": stage},
    )
    accepted = client.post(
        f"/api/voc/{case_id}/stage",
        headers=WRITER_HEADERS,
        json={"stage": stage, reason_field: "Customer withdrew request"},
    )

    assert missing.status_code == 422
    assert accepted.status_code == 200
