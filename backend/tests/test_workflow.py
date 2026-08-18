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

        def change_stage(self, case_id, values, writer_name, require_approvals=False):
            from app.repositories.collaboration import ApprovalRequired

            raise ApprovalRequired

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
            if "SELECT voc_request_id" in query:
                return Result({"voc_request_id": 3})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 3})
            if "FROM public.department_tasks" in query and "FOR UPDATE" in query:
                return Result({"id": 5, "voc_request_id": 3, "status": "in_progress", "response_content": None})
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


def test_task_revision_invalidates_older_manager_approval_without_timestamps():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def execute(self, query, params=()):
            normalized = " ".join(query.split()).lower()
            uses_revision_invariant = (
                "task_revision" in normalized
                and "task.revision" in normalized
                and "updated_at" not in normalized
            )
            return Result({"approved": not uses_revision_invariant})

    @contextmanager
    def connection_factory():
        yield Connection()

    assert CollaborationRepository(connection_factory).approvals_complete(1) is False


def test_task_update_monotonically_increments_revision():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.update_query = None

        def execute(self, query, params=()):
            if "SELECT voc_request_id" in query:
                return Result({"voc_request_id": 3})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 3})
            if "FROM public.department_tasks" in query and "FOR UPDATE" in query:
                return Result({"id": 5, "voc_request_id": 3, "revision": 4})
            if "UPDATE public.department_tasks" in query:
                self.update_query = " ".join(query.split()).lower()
                return Result({"id": 5, "voc_request_id": 3, "revision": 5})
            return Result()

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    updated = CollaborationRepository(connection_factory).update_task(
        5, {"status": "completed"}, "Kim"
    )

    assert updated["revision"] == 5
    assert "revision = revision + 1" in connection.update_query


def test_final_approval_requires_fresh_manager_approvals_in_locked_round():
    from app.repositories.collaboration import ApprovalRequired, CollaborationRepository

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))
            if "SELECT voc_request_id" in query:
                return Result({"voc_request_id": 3})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 3})
            if "FROM public.department_tasks" in query and "FOR UPDATE" in query:
                return Result({"id": 5, "voc_request_id": 3, "revision": 2})
            if "master_final_approvers" in query:
                return Result({"name": "Kim"})
            if "AS approved" in query:
                return Result({"approved": False})
            raise AssertionError("final review must not be inserted")

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    with pytest.raises(ApprovalRequired):
        CollaborationRepository(connection_factory).review_task(
            5,
            {"reviewer_role": "final_approver", "decision": "approved"},
            "Kim",
        )

    assert any("FOR UPDATE" in query for query, _ in connection.calls)
    assert not any("INSERT INTO public.task_reviews" in query for query, _ in connection.calls)


def test_customer_reply_requires_final_review_after_every_manager_review():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, row):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def execute(self, query, params=()):
            normalized = " ".join(query.split()).lower()
            if "latest_final as" not in normalized:
                return Result(
                    {
                        "approved": "task_revision" in normalized
                        and "task.revision" in normalized
                    }
                )
            ordered = (
                "task_revision" in normalized
                and "task.revision" in normalized
                and "final" in normalized
                and "manager" in normalized
                and "reviewed_at" not in normalized
                and (
                    "final.id >" in normalized
                    or "final_review.id >" in normalized
                    or "final_review_id >" in normalized
                )
            )
            return Result({"approved": ordered})

    @contextmanager
    def connection_factory():
        yield Connection()

    assert CollaborationRepository(connection_factory).approvals_complete(3) is True


def test_fixed_final_approver_is_revalidated_inside_locked_review_transaction():
    from app.repositories.collaboration import (
        CollaborationRepository,
        FinalApproverMismatch,
    )

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))
            if "SELECT voc_request_id" in query:
                return Result({"voc_request_id": 3})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 3})
            if "FROM public.department_tasks" in query and "FOR UPDATE" in query:
                return Result({"id": 5, "voc_request_id": 3, "revision": 2})
            if "master_final_approvers" in query:
                return Result(None)
            raise AssertionError("unconfigured final approver must not insert review")

    connection = Connection()
    entries = 0

    @contextmanager
    def connection_factory():
        nonlocal entries
        entries += 1
        yield connection

    with pytest.raises(FinalApproverMismatch):
        CollaborationRepository(connection_factory).review_task(
            5,
            {"reviewer_role": "final_approver", "decision": "approved"},
            "Kim",
        )

    assert entries == 1
    round_lock = next(
        index
        for index, (query, _) in enumerate(connection.calls)
        if "FROM public.voc_requests" in query and "FOR UPDATE" in query
    )
    identity_check = next(
        index
        for index, (query, _) in enumerate(connection.calls)
        if "master_final_approvers" in query
    )
    assert round_lock < identity_check


def test_customer_reply_approval_check_and_stage_change_share_locked_transaction():
    from app.repositories.collaboration import ApprovalRequired, CollaborationRepository

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((query, params))
            if "FROM public.voc_requests" in query:
                return Result({"id": 3, "case_id": "VOC-2026-0001", "stage": "final_review"})
            if "AS approved" in query:
                return Result({"approved": False})
            raise AssertionError(query)

    connection = Connection()
    entries = 0

    @contextmanager
    def connection_factory():
        nonlocal entries
        entries += 1
        yield connection

    with pytest.raises(ApprovalRequired):
        CollaborationRepository(connection_factory).change_stage(
            "VOC-2026-0001",
            {"stage": "customer_reply"},
            "Kim",
            require_approvals=True,
        )

    assert entries == 1
    assert any(
        "FROM public.voc_requests" in query and "FOR UPDATE" in query
        for query, _ in connection.calls
    )
    assert not any("UPDATE public.voc_requests" in query for query, _ in connection.calls)


@pytest.mark.parametrize("terminal_stage", ["cancelled", "deleted"])
def test_terminal_stage_cannot_be_reversed(terminal_stage):
    from app.services.workflow import WorkflowService

    class Repository:
        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 1, "stage": terminal_stage}]}

        def change_stage(self, case_id, values, writer_name, require_approvals=False):
            raise AssertionError("terminal transition must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).change_stage(
            "VOC-2026-0001", {"stage": "received", "reason": "restore"}, "Kim"
        )

    assert error.value.status_code == 409


def test_forward_stage_jump_is_rejected():
    from app.services.workflow import WorkflowService

    class Repository:
        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 1, "stage": "received"}]}

        def change_stage(self, case_id, values, writer_name, require_approvals=False):
            raise AssertionError("invalid jump must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).change_stage(
            "VOC-2026-0001", {"stage": "department_work"}, "Kim"
        )

    assert error.value.status_code == 409


def test_department_manager_review_requires_matching_task_manager():
    from app.services.workflow import WorkflowService

    class Repository:
        def get_task(self, task_id):
            return {"id": task_id, "manager_name": "Lee", "status": "completed"}

        def review_task(self, task_id, values, writer_name):
            raise AssertionError("wrong manager must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).review_task(
            4,
            {"reviewer_role": "department_manager", "decision": "approved"},
            "Kim",
        )

    assert error.value.status_code == 403


def test_overdue_task_is_first_marked_delayed_then_can_complete():
    from app.services.workflow import WorkflowService

    class Repository:
        def __init__(self):
            self.task = {
                "id": 7,
                "due_date": date(2026, 8, 17),
                "status": "in_progress",
                "response_content": "Root cause confirmed",
                "delay_reason": None,
            }

        def get_task(self, task_id):
            return dict(self.task)

        def update_task(self, task_id, changes, writer_name):
            self.task.update(changes)
            return dict(self.task)

    repository = Repository()
    service = WorkflowService(repository, today=lambda: date(2026, 8, 18))

    delayed = service.update_task(
        7,
        {"status": "completed", "delay_reason": "Supplier evidence arrived late"},
        "Kim",
    )
    completed = service.update_task(7, {"status": "completed"}, "Kim")

    assert delayed["status"] == "delayed"
    assert completed["status"] == "completed"


def test_omitted_follow_up_sender_fields_preserve_prior_identity():
    from app.services.workflow import WorkflowService

    class Repository:
        def __init__(self):
            self.values = None

        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 1, "stage": "customer_reply"}]}

        def create_round(self, case_id, values, writer_name):
            self.values = values
            return {"case_id": case_id, "round_number": 2}

    repository = Repository()
    WorkflowService(repository).create_round(
        "VOC-2026-0001", {"customer_request": "Follow-up"}, "Kim"
    )

    assert "sender_name" not in repository.values
    assert "sender_email" not in repository.values
    assert "sender_company" not in repository.values


@pytest.mark.parametrize("stage", ["received", "in_progress", "cancelled", "deleted"])
def test_follow_up_round_requires_replied_or_completed_case(stage):
    from app.services.workflow import WorkflowService

    class Repository:
        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 1, "stage": stage}]}

        def create_round(self, case_id, values, writer_name):
            raise AssertionError("invalid follow-up must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).create_round(
            "VOC-2026-0001", {"customer_request": "Follow-up"}, "Kim"
        )

    assert error.value.status_code == 409


def test_no_op_task_update_is_rejected():
    from app.services.workflow import WorkflowService

    class Repository:
        def get_task(self, task_id):
            return {"id": task_id, "status": "in_progress", "due_date": date(2026, 8, 20)}

        def update_task(self, task_id, changes, writer_name):
            raise AssertionError("no-op must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository(), today=lambda: date(2026, 8, 18)).update_task(
            7, {"status": "in_progress"}, "Kim"
        )

    assert error.value.status_code == 422


def test_stage_transition_is_revalidated_under_repository_lock():
    from app.repositories.collaboration import (
        CollaborationRepository,
        StageTransitionNotAllowed,
    )

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
            if "FROM public.voc_requests" in query:
                return Result({"id": 1, "stage": "received"})
            raise AssertionError("invalid transition must not update")

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    with pytest.raises(StageTransitionNotAllowed):
        CollaborationRepository(connection_factory).change_stage(
            "VOC-2026-0001", {"stage": "department_work"}, "Kim"
        )

    assert "FOR UPDATE" in connection.calls[0][0]


def test_manager_identity_is_revalidated_under_review_transaction_lock():
    from app.repositories.collaboration import CollaborationRepository, ReviewerMismatch

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
            if "FROM public.department_tasks" in query:
                return Result({"id": 4, "voc_request_id": 1, "manager_name": "Lee"})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 1})
            raise AssertionError("wrong manager must not insert review")

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    with pytest.raises(ReviewerMismatch):
        CollaborationRepository(connection_factory).review_task(
            4,
            {"reviewer_role": "department_manager", "decision": "approved"},
            "Kim",
        )

    assert any(
        "FROM public.voc_requests" in query and "FOR UPDATE" in query
        for query, _ in connection.calls
    )


@pytest.mark.parametrize("target", ["cancelled", "deleted"])
def test_terminal_transition_requires_specific_reason_at_service_boundary(target):
    from app.services.workflow import WorkflowService

    class Repository:
        def get_case(self, case_id):
            return {"case_id": case_id, "rounds": [{"id": 1, "stage": "received"}]}

        def change_stage(self, case_id, values, writer_name, require_approvals=False):
            raise AssertionError("missing terminal reason must not reach repository")

    with pytest.raises(HTTPException) as error:
        WorkflowService(Repository()).change_stage(
            "VOC-2026-0001", {"stage": target}, "Kim"
        )

    assert error.value.status_code == 422


def test_task_update_locks_parent_round_before_task_mutation():
    from app.repositories.collaboration import CollaborationRepository

    class Result:
        def __init__(self, row=None):
            self.row = row

        def fetchone(self):
            return self.row

    class Connection:
        def __init__(self):
            self.calls = []

        def execute(self, query, params=()):
            self.calls.append((" ".join(query.split()), params))
            if "SELECT voc_request_id FROM public.department_tasks" in query:
                return Result({"voc_request_id": 3})
            if "FROM public.voc_requests" in query and "FOR UPDATE" in query:
                return Result({"id": 3})
            if "FROM public.department_tasks" in query and "FOR UPDATE" in query:
                return Result({"id": 5, "voc_request_id": 3, "status": "in_progress"})
            if "UPDATE public.department_tasks" in query:
                return Result({"id": 5, "voc_request_id": 3, "status": "completed"})
            return Result()

    connection = Connection()

    @contextmanager
    def connection_factory():
        yield connection

    CollaborationRepository(connection_factory).update_task(
        5, {"status": "completed"}, "Kim"
    )

    round_lock = next(
        index
        for index, (query, _) in enumerate(connection.calls)
        if "FROM public.voc_requests" in query and "FOR UPDATE" in query
    )
    task_lock = next(
        index
        for index, (query, _) in enumerate(connection.calls)
        if "FROM public.department_tasks" in query and "FOR UPDATE" in query
    )
    assert round_lock < task_lock
