from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from psycopg.types.json import Jsonb

from app.db import database_connection


REQUEST_COLUMNS = (
    "customer_request",
    "original_mail_body",
    "sender_name",
    "sender_email",
    "sender_company",
    "translation_draft",
    "translation_final",
    "voc_type",
    "voc_subtype",
    "product_equipment",
    "priority",
)
TASK_COLUMNS = (
    "department",
    "assignee_name",
    "assignee_email",
    "manager_name",
    "manager_email",
    "status",
    "response_content",
    "due_date",
    "delay_reason",
    "ecm_link",
)


class ApprovalRequired(Exception):
    pass


class RoundNotAllowed(Exception):
    pass


class ReviewerMismatch(Exception):
    pass


class FinalApproverMismatch(Exception):
    pass


class StageTransitionNotAllowed(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


STAGES = [
    "received",
    "managing",
    "in_progress",
    "department_work",
    "department_review",
    "manager_review",
    "final_review",
    "customer_reply",
    "completed",
]
TERMINAL_STAGES = {"cancelled", "deleted"}


def validate_stage_transition(
    current: str,
    target: str,
    reason: str | None = None,
    terminal_reason: str | None = None,
) -> None:
    if current in TERMINAL_STAGES:
        raise StageTransitionNotAllowed(409, "Terminal stage cannot change")
    if target == current:
        raise StageTransitionNotAllowed(422, "Stage is unchanged")
    if target in TERMINAL_STAGES:
        if not terminal_reason:
            raise StageTransitionNotAllowed(
                422, f"{target} stage requires its specific reason"
            )
        return
    current_index = STAGES.index(current)
    target_index = STAGES.index(target)
    if target_index > current_index + 1:
        raise StageTransitionNotAllowed(409, "Stage transition is not allowed")
    if target_index < current_index and not reason:
        raise StageTransitionNotAllowed(
            422, "Reverse stage transitions require reason"
        )


class CollaborationRepository:
    def __init__(self, connection_factory: Callable = database_connection):
        self.connection_factory = connection_factory

    @staticmethod
    def _audit(
        connection,
        entity_type: str,
        entity_id: Any,
        action: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        writer_name: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO public.change_audits (
                entity_type, entity_id, action, before_values,
                after_values, writer_name
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                entity_type,
                str(entity_id),
                action,
                Jsonb(jsonable_encoder(before)) if before is not None else None,
                Jsonb(jsonable_encoder(after)) if after is not None else None,
                writer_name,
            ),
        )

    def create_voc(
        self,
        values: dict[str, Any],
        tasks: list[dict[str, Any]],
        writer_name: str,
        year: int,
    ) -> dict[str, Any]:
        with self.connection_factory() as connection:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (f"voc-case-{year}",),
            )
            row = connection.execute(
                """
                SELECT coalesce(max(right(case_id, 4)::integer), 0) + 1 AS sequence
                FROM public.voc_requests
                WHERE case_id LIKE %s
                """,
                (f"VOC-{year}-%",),
            ).fetchone()
            case_id = f"VOC-{year}-{int(row['sequence']):04d}"
            created = self._insert_request(
                connection, case_id, 1, values, writer_name
            )
            created_tasks = [
                self._insert_task(connection, created["id"], task, writer_name)
                for task in tasks
            ]
            self._audit(
                connection,
                "voc_request",
                case_id,
                "created",
                None,
                created,
                writer_name,
            )
            for task in created_tasks:
                self._audit(
                    connection,
                    "department_task",
                    task["id"],
                    "created",
                    None,
                    task,
                    writer_name,
                )
        return {**created, "tasks": created_tasks, "reviews": []}

    def create_round(
        self, case_id: str, values: dict[str, Any], writer_name: str
    ) -> dict[str, Any] | None:
        values = dict(values)
        requested_tasks = values.pop("tasks", None)
        with self.connection_factory() as connection:
            previous = connection.execute(
                """
                SELECT * FROM public.voc_requests
                WHERE case_id = %s
                ORDER BY round_number DESC
                LIMIT 1 FOR UPDATE
                """,
                (case_id,),
            ).fetchone()
            if previous is None:
                return None
            if previous["stage"] not in {"customer_reply", "completed"}:
                raise RoundNotAllowed(
                    "Follow-up rounds require customer_reply or completed stage"
                )
            source = {
                column: values.get(column, previous.get(column))
                for column in REQUEST_COLUMNS
            }
            created = self._insert_request(
                connection,
                case_id,
                previous["round_number"] + 1,
                source,
                writer_name,
            )
            if requested_tasks is None:
                prior_tasks = connection.execute(
                    """
                    SELECT department, assignee_name, assignee_email,
                           manager_name, manager_email, due_date, ecm_link
                    FROM public.department_tasks
                    WHERE voc_request_id = %s AND status <> 'excluded'
                    ORDER BY id
                    """,
                    (previous["id"],),
                ).fetchall()
                requested_tasks = [dict(task) for task in prior_tasks]
            created_tasks = [
                self._insert_task(connection, created["id"], task, writer_name)
                for task in requested_tasks
            ]
            self._audit(
                connection,
                "voc_request",
                case_id,
                "round_created",
                previous,
                created,
                writer_name,
            )
            for task in created_tasks:
                self._audit(
                    connection,
                    "department_task",
                    task["id"],
                    "reopened",
                    None,
                    task,
                    writer_name,
                )
        return {**created, "tasks": created_tasks, "reviews": []}

    @staticmethod
    def _insert_request(
        connection,
        case_id: str,
        round_number: int,
        values: dict[str, Any],
        writer_name: str,
    ) -> dict[str, Any]:
        selected = {column: values.get(column) for column in REQUEST_COLUMNS}
        selected["original_mail_body"] = selected["original_mail_body"] or ""
        selected["priority"] = selected["priority"] or "normal"
        columns = ("case_id", "round_number", *selected.keys(), "created_by")
        params = (case_id, round_number, *selected.values(), writer_name)
        return connection.execute(
            f"INSERT INTO public.voc_requests ({', '.join(columns)}) "
            f"VALUES ({', '.join(['%s'] * len(columns))}) RETURNING *",
            params,
        ).fetchone()

    @staticmethod
    def _insert_task(
        connection,
        request_id: int,
        values: dict[str, Any],
        writer_name: str,
    ) -> dict[str, Any]:
        selected = {
            column: values[column]
            for column in TASK_COLUMNS
            if column in values and values[column] is not None
        }
        selected.setdefault("status", "not_started")
        columns = ("voc_request_id", *selected.keys(), "created_by")
        params = (request_id, *selected.values(), writer_name)
        return connection.execute(
            f"INSERT INTO public.department_tasks ({', '.join(columns)}) "
            f"VALUES ({', '.join(['%s'] * len(columns))}) RETURNING *",
            params,
        ).fetchone()

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with self.connection_factory() as connection:
            return connection.execute(
                "SELECT * FROM public.department_tasks WHERE id = %s",
                (task_id,),
            ).fetchone()

    @staticmethod
    def _lock_task_round(connection, task_id: int) -> dict[str, Any] | None:
        reference = connection.execute(
            "SELECT voc_request_id FROM public.department_tasks WHERE id = %s",
            (task_id,),
        ).fetchone()
        if reference is None:
            return None
        connection.execute(
            "SELECT id FROM public.voc_requests WHERE id = %s FOR UPDATE",
            (reference["voc_request_id"],),
        )
        return connection.execute(
            "SELECT * FROM public.department_tasks WHERE id = %s FOR UPDATE",
            (task_id,),
        ).fetchone()

    def update_task(
        self, task_id: int, changes: dict[str, Any], writer_name: str
    ) -> dict[str, Any] | None:
        selected = {
            column: changes[column]
            for column in TASK_COLUMNS
            if column in changes
        }
        with self.connection_factory() as connection:
            before = self._lock_task_round(connection, task_id)
            if before is None:
                return None
            assignments = ", ".join(f"{column} = %s" for column in selected)
            after = connection.execute(
                f"UPDATE public.department_tasks SET {assignments}, "
                "revision = revision + 1, updated_at = now() "
                "WHERE id = %s RETURNING *",
                (*selected.values(), task_id),
            ).fetchone()
            self._audit(
                connection,
                "department_task",
                task_id,
                "updated",
                before,
                after,
                writer_name,
            )
        return after

    def review_task(
        self, task_id: int, values: dict[str, Any], writer_name: str
    ) -> dict[str, Any]:
        with self.connection_factory() as connection:
            task = self._lock_task_round(connection, task_id)
            if (
                values["reviewer_role"] == "department_manager"
                and task["manager_name"] != writer_name
            ):
                raise ReviewerMismatch
            if values["reviewer_role"] == "final_approver":
                configured = connection.execute(
                    """
                    SELECT person.name
                    FROM public.master_final_approvers AS final
                    JOIN public.master_people AS person ON person.id = final.person_id
                    WHERE person.active AND person.name = %s
                    """,
                    (writer_name,),
                ).fetchone()
                if configured is None:
                    raise FinalApproverMismatch
                if (
                    values["decision"] == "approved"
                    and not self._manager_approvals_complete(
                        connection, task["voc_request_id"]
                    )
                ):
                    raise ApprovalRequired
            review = connection.execute(
                """
                INSERT INTO public.task_reviews (
                    voc_request_id, task_id, reviewer_role, decision,
                    task_revision, comment, reviewed_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    task["voc_request_id"],
                    task_id,
                    values["reviewer_role"],
                    values["decision"],
                    task["revision"],
                    values.get("comment"),
                    writer_name,
                ),
            ).fetchone()
            self._audit(
                connection,
                "task_review",
                review["id"],
                "created",
                None,
                review,
                writer_name,
            )
            if values["decision"] == "rejected":
                after = connection.execute(
                    """
                    UPDATE public.department_tasks
                    SET status = 'reviewing', revision = revision + 1,
                        updated_at = now()
                    WHERE id = %s RETURNING *
                    """,
                    (task_id,),
                ).fetchone()
                self._audit(
                    connection,
                    "department_task",
                    task_id,
                    "review_rejected",
                    task,
                    after,
                    writer_name,
                )
        return review

    def approvals_complete(self, request_id: int) -> bool:
        with self.connection_factory() as connection:
            return self._approvals_complete(connection, request_id)

    @staticmethod
    def _manager_approvals_complete(connection, request_id: int) -> bool:
        row = connection.execute(
                """
                WITH active_tasks AS (
                    SELECT id, status, revision
                    FROM public.department_tasks
                    WHERE voc_request_id = %s AND status <> 'excluded'
                ), latest_manager AS (
                    SELECT DISTINCT ON (task_id)
                           id, task_id, decision, task_revision
                    FROM public.task_reviews
                    WHERE voc_request_id = %s
                      AND reviewer_role = 'department_manager'
                    ORDER BY task_id, id DESC
                )
                SELECT NOT EXISTS (
                           SELECT 1 FROM active_tasks AS task
                           LEFT JOIN latest_manager AS review ON review.task_id = task.id
                           WHERE task.status <> 'completed'
                              OR review.decision IS DISTINCT FROM 'approved'
                              OR review.task_revision IS DISTINCT FROM task.revision
                       ) AS approved
                """,
                (request_id, request_id),
            ).fetchone()
        return bool(row["approved"])

    @classmethod
    def _approvals_complete(cls, connection, request_id: int) -> bool:
        if not cls._manager_approvals_complete(connection, request_id):
            return False
        row = connection.execute(
            """
            WITH active_tasks AS (
                SELECT id, revision
                FROM public.department_tasks
                WHERE voc_request_id = %s AND status <> 'excluded'
            ), latest_manager AS (
                SELECT DISTINCT ON (task_id)
                       id, task_id, task_revision
                FROM public.task_reviews
                WHERE voc_request_id = %s
                  AND reviewer_role = 'department_manager'
                ORDER BY task_id, id DESC
            ), latest_final AS (
                SELECT id, decision
                FROM public.task_reviews
                WHERE voc_request_id = %s
                  AND reviewer_role = 'final_approver'
                ORDER BY id DESC
                LIMIT 1
            )
            SELECT EXISTS (
                SELECT 1
                FROM latest_final AS final_review
                WHERE final_review.decision = 'approved'
                  AND final_review.id > (
                      SELECT coalesce(max(manager.id), 0)
                      FROM active_tasks AS task
                      JOIN latest_manager AS manager ON manager.task_id = task.id
                      WHERE manager.task_revision = task.revision
                  )
            ) AS approved
            """,
            (request_id, request_id, request_id),
        ).fetchone()
        return bool(row["approved"])

    def change_stage(
        self,
        case_id: str,
        values: dict[str, Any],
        writer_name: str,
        require_approvals: bool = False,
    ) -> dict[str, Any] | None:
        with self.connection_factory() as connection:
            before = connection.execute(
                """
                SELECT * FROM public.voc_requests
                WHERE case_id = %s
                ORDER BY round_number DESC
                LIMIT 1 FOR UPDATE
                """,
                (case_id,),
            ).fetchone()
            if before is None:
                return None
            validate_stage_transition(
                before["stage"],
                values["stage"],
                values.get("reason"),
                values.get(
                    "cancellation_reason"
                    if values["stage"] == "cancelled"
                    else "deletion_reason"
                ),
            )
            if require_approvals and not self._approvals_complete(
                connection, before["id"]
            ):
                raise ApprovalRequired
            after = connection.execute(
                """
                UPDATE public.voc_requests
                SET stage = %s, cancellation_reason = %s,
                    deletion_reason = %s, updated_at = now()
                WHERE id = %s RETURNING *
                """,
                (
                    values["stage"],
                    values.get("cancellation_reason"),
                    values.get("deletion_reason"),
                    before["id"],
                ),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO public.voc_stage_history (
                    voc_request_id, from_stage, to_stage, reason,
                    ecm_link, changed_by
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    before["id"],
                    before["stage"],
                    values["stage"],
                    values.get("reason"),
                    values.get("ecm_link"),
                    writer_name,
                ),
            )
            self._audit(
                connection,
                "voc_stage",
                case_id,
                "changed",
                before,
                after,
                writer_name,
            )
        return after

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with self.connection_factory() as connection:
            rounds = connection.execute(
                """
                SELECT * FROM public.voc_requests
                WHERE case_id = %s ORDER BY round_number
                """,
                (case_id,),
            ).fetchall()
            if not rounds:
                return None
            request_ids = [row["id"] for row in rounds]
            tasks = connection.execute(
                """
                SELECT * FROM public.department_tasks
                WHERE voc_request_id = ANY(%s) ORDER BY id
                """,
                (request_ids,),
            ).fetchall()
            reviews = connection.execute(
                """
                SELECT * FROM public.task_reviews
                WHERE voc_request_id = ANY(%s) ORDER BY reviewed_at, id
                """,
                (request_ids,),
            ).fetchall()
            history = connection.execute(
                """
                SELECT * FROM public.voc_stage_history
                WHERE voc_request_id = ANY(%s) ORDER BY changed_at, id
                """,
                (request_ids,),
            ).fetchall()
            task_ids = [str(task["id"]) for task in tasks]
            review_ids = [str(review["id"]) for review in reviews]
            audits = connection.execute(
                """
                SELECT * FROM public.change_audits
                WHERE (entity_type IN ('voc_request', 'voc_stage') AND entity_id = %s)
                   OR (entity_type = 'department_task' AND entity_id = ANY(%s))
                   OR (entity_type = 'task_review' AND entity_id = ANY(%s))
                ORDER BY changed_at, id
                """,
                (case_id, task_ids or [""], review_ids or [""]),
            ).fetchall()
        expanded = []
        for request in rounds:
            request_id = request["id"]
            expanded.append(
                {
                    **request,
                    "tasks": [
                        task for task in tasks if task["voc_request_id"] == request_id
                    ],
                    "reviews": [
                        review
                        for review in reviews
                        if review["voc_request_id"] == request_id
                    ],
                    "stage_history": [
                        item
                        for item in history
                        if item["voc_request_id"] == request_id
                    ],
                }
            )
        return {"case_id": case_id, "rounds": expanded, "audits": audits}
