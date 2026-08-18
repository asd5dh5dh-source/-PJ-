from contextlib import contextmanager
from datetime import date

import pytest
from fastapi import HTTPException


def test_mail_parser_extracts_sender_email_and_explicit_company_only():
    from app.services.mail_parser import parse_sender

    parsed = parse_sender(
        "From: Jane Doe <jane@example.com>\n"
        "Company: Example Materials\n"
        "Subject: Urgent separator failure\n\n"
        "Please classify this as a quality complaint for Product X."
    )

    assert parsed == {
        "sender_name": "Jane Doe",
        "sender_email": "jane@example.com",
        "sender_company": "Example Materials",
    }


def test_mail_parser_leaves_ambiguous_company_empty():
    from app.services.mail_parser import parse_sender

    parsed = parse_sender(
        "From: Jane Doe <jane@example.com>\n"
        "Subject: Message from Example Materials\n\nPlease investigate."
    )

    assert parsed["sender_company"] is None


def test_overdue_completion_requires_delay_reason_before_it_can_complete():
    from app.services.workflow import WorkflowService

    class Repository:
        def __init__(self):
            self.changes = None

        def get_task(self, task_id):
            return {"id": task_id, "due_date": date(2026, 8, 17), "status": "in_progress"}

        def update_task(self, task_id, changes, writer_name):
            self.changes = changes
            return {"id": task_id, **changes}

    repository = Repository()
    with pytest.raises(HTTPException) as error:
        WorkflowService(repository, today=lambda: date(2026, 8, 18)).update_task(
            7,
            {
                "status": "completed",
                "response_content": "Root cause confirmed",
                "due_date": date(2026, 8, 17),
            },
            "Kim",
        )

    assert error.value.status_code == 422
    assert repository.changes is None


def test_customer_reply_requires_active_task_and_final_approvals():
    from app.services.workflow import WorkflowService

    class Repository:
        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 9, "stage": "final_review"}]}

        def approvals_complete(self, request_id):
            return False

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).change_stage(
            "VOC-2026-0001", {"stage": "customer_reply"}, "Kim"
        )

    assert error.value.status_code == 409


def test_task_update_and_audit_share_one_repository_transaction():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))
            if "FOR UPDATE" in query:
                return Result({"id": 5, "status": "in_progress", "response_content": None})
            if "UPDATE public.department_tasks" in query:
                return Result({"id": 5, "status": "completed", "response_content": "Done"})
            return Result(None)

    connection = Connection()
    entries = 0

    @contextmanager
    def connection_factory():
        nonlocal entries
        entries += 1
        yield connection

    result = CollaborationRepository(connection_factory).update_task(
        5, {"status": "completed", "response_content": "Done"}, "Kim"
    )

    assert result["status"] == "completed"
    assert entries == 1
    assert any("UPDATE public.department_tasks" in query for query, _ in connection.calls)
    assert any("INSERT INTO public.change_audits" in query for query, _ in connection.calls)


def test_voc_detail_includes_task_review_audits():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, rows):
            self.rows = rows

        def fetchall(self):
            return self.rows

    class Connection:
        def execute(self, query, params=()):
            if "FROM public.voc_requests" in query:
                return Result([{"id": 1, "case_id": "VOC-2026-0001", "round_number": 1}])
            if "FROM public.department_tasks" in query:
                return Result([{"id": 5, "voc_request_id": 1}])
            if "FROM public.task_reviews" in query:
                return Result([{"id": 8, "voc_request_id": 1, "task_id": 5}])
            if "FROM public.voc_stage_history" in query:
                return Result([])
            if "FROM public.change_audits" in query:
                return Result(
                    [{"entity_type": "task_review", "entity_id": "8"}]
                    if len(params) == 3 and "8" in params[2]
                    else [{"entity_type": "unrelated", "entity_id": "8"}]
                )
            raise AssertionError(query)

    @contextmanager
    def connection_factory():
        yield Connection()

    detail = CollaborationRepository(connection_factory).get_case("VOC-2026-0001")

    assert detail["audits"] == [{"entity_type": "task_review", "entity_id": "8"}]
