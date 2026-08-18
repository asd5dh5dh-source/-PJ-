CREATE TABLE IF NOT EXISTS public.writer_attempts (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    writer_name text NOT NULL CHECK (btrim(writer_name) <> ''),
    client_ip text NOT NULL CHECK (btrim(client_ip) <> ''),
    succeeded boolean NOT NULL,
    attempted_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_writer_attempts_ip_lockout
    ON public.writer_attempts (client_ip, attempted_at DESC);

CREATE TABLE IF NOT EXISTS public.voc_requests (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id text NOT NULL CHECK (case_id ~ '^VOC-[0-9]{4}-[0-9]{4}$'),
    round_number integer NOT NULL CHECK (round_number > 0),
    customer_request text NOT NULL CHECK (btrim(customer_request) <> ''),
    original_mail_body text NOT NULL DEFAULT '',
    sender_name text,
    sender_email text,
    sender_company text,
    translation_draft text,
    translation_final text,
    voc_type text,
    voc_subtype text,
    product_equipment text,
    priority text NOT NULL DEFAULT 'normal'
        CHECK (priority IN ('normal', 'high')),
    stage text NOT NULL DEFAULT 'received'
        CHECK (stage IN (
            'received', 'managing', 'in_progress', 'department_work',
            'department_review', 'manager_review', 'final_review',
            'customer_reply', 'completed', 'cancelled', 'deleted'
        )),
    cancellation_reason text,
    deletion_reason text,
    created_by text NOT NULL CHECK (btrim(created_by) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, round_number),
    CHECK (
        stage <> 'cancelled'
        OR coalesce(btrim(cancellation_reason), '') <> ''
    ),
    CHECK (stage <> 'deleted' OR coalesce(btrim(deletion_reason), '') <> '')
);

CREATE INDEX IF NOT EXISTS idx_voc_requests_case_round
    ON public.voc_requests (case_id, round_number DESC);
CREATE INDEX IF NOT EXISTS idx_voc_requests_stage_created
    ON public.voc_requests (stage, created_at DESC);

CREATE TABLE IF NOT EXISTS public.department_tasks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voc_request_id bigint NOT NULL
        REFERENCES public.voc_requests(id) ON DELETE RESTRICT,
    department text NOT NULL CHECK (btrim(department) <> ''),
    assignee_name text,
    assignee_email text,
    manager_name text,
    manager_email text,
    status text NOT NULL DEFAULT 'not_started'
        CHECK (status IN (
            'not_started', 'reviewing', 'in_progress',
            'completed', 'delayed', 'excluded'
        )),
    response_content text,
    due_date date,
    delay_reason text,
    ecm_link text,
    revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_by text NOT NULL CHECK (btrim(created_by) <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT department_tasks_id_request_unique UNIQUE (id, voc_request_id),
    CHECK (status <> 'delayed' OR coalesce(btrim(delay_reason), '') <> '')
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.department_tasks'::regclass
          AND conname = 'department_tasks_id_request_unique'
    ) THEN
        ALTER TABLE public.department_tasks
            ADD CONSTRAINT department_tasks_id_request_unique
            UNIQUE (id, voc_request_id);
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_department_tasks_request
    ON public.department_tasks (voc_request_id, status);
CREATE INDEX IF NOT EXISTS idx_department_tasks_due_date
    ON public.department_tasks (due_date)
    WHERE status NOT IN ('completed', 'excluded');

ALTER TABLE public.department_tasks
    ADD COLUMN IF NOT EXISTS revision bigint NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS public.task_reviews (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voc_request_id bigint NOT NULL
        REFERENCES public.voc_requests(id) ON DELETE RESTRICT,
    task_id bigint,
    reviewer_role text NOT NULL
        CHECK (reviewer_role IN ('department_manager', 'final_approver')),
    decision text NOT NULL CHECK (decision IN ('approved', 'rejected')),
    task_revision bigint,
    comment text,
    reviewed_by text NOT NULL CHECK (btrim(reviewed_by) <> ''),
    reviewed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT task_reviews_task_request_fk
        FOREIGN KEY (task_id, voc_request_id)
        REFERENCES public.department_tasks(id, voc_request_id)
        ON DELETE RESTRICT,
    CHECK (reviewer_role <> 'department_manager' OR task_id IS NOT NULL)
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.task_reviews'::regclass
          AND conname = 'task_reviews_task_request_fk'
    ) THEN
        ALTER TABLE public.task_reviews
            ADD CONSTRAINT task_reviews_task_request_fk
            FOREIGN KEY (task_id, voc_request_id)
            REFERENCES public.department_tasks(id, voc_request_id)
            ON DELETE RESTRICT;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_task_reviews_request
    ON public.task_reviews (voc_request_id, reviewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_task_reviews_task
    ON public.task_reviews (task_id, reviewed_at DESC);

ALTER TABLE public.task_reviews
    ADD COLUMN IF NOT EXISTS task_revision bigint;

CREATE TABLE IF NOT EXISTS public.voc_stage_history (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voc_request_id bigint NOT NULL
        REFERENCES public.voc_requests(id) ON DELETE RESTRICT,
    from_stage text,
    to_stage text NOT NULL CHECK (btrim(to_stage) <> ''),
    reason text,
    ecm_link text,
    changed_by text NOT NULL CHECK (btrim(changed_by) <> ''),
    changed_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_voc_stage_history_request
    ON public.voc_stage_history (voc_request_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS public.change_audits (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type text NOT NULL CHECK (btrim(entity_type) <> ''),
    entity_id text NOT NULL CHECK (btrim(entity_id) <> ''),
    action text NOT NULL CHECK (btrim(action) <> ''),
    before_values jsonb,
    after_values jsonb,
    writer_name text NOT NULL CHECK (btrim(writer_name) <> ''),
    changed_at timestamptz NOT NULL DEFAULT now(),
    CHECK (before_values IS NULL OR jsonb_typeof(before_values) = 'object'),
    CHECK (after_values IS NULL OR jsonb_typeof(after_values) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_change_audits_entity
    ON public.change_audits (entity_type, entity_id, changed_at DESC);

CREATE TABLE IF NOT EXISTS public.notification_logs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voc_request_id bigint
        REFERENCES public.voc_requests(id) ON DELETE RESTRICT,
    task_id bigint REFERENCES public.department_tasks(id) ON DELETE RESTRICT,
    recipients jsonb NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(recipients) = 'array'),
    subject text NOT NULL,
    body text NOT NULL,
    scheduled_at timestamptz,
    sent_at timestamptz,
    runtime_profile text NOT NULL
        CHECK (runtime_profile IN ('external_review', 'internal')),
    delivery_status text NOT NULL DEFAULT 'preview'
        CHECK (delivery_status IN ('preview', 'pending', 'sent', 'failed')),
    real_delivery boolean NOT NULL DEFAULT false,
    error_message text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT notification_logs_external_preview_only CHECK (
        runtime_profile <> 'external_review'
        OR (
            delivery_status = 'preview'
            AND NOT real_delivery
            AND sent_at IS NULL
        )
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.notification_logs'::regclass
          AND conname = 'notification_logs_external_preview_only'
    ) THEN
        ALTER TABLE public.notification_logs
            ADD CONSTRAINT notification_logs_external_preview_only
            CHECK (
                runtime_profile <> 'external_review'
                OR (
                    delivery_status = 'preview'
                    AND NOT real_delivery
                    AND sent_at IS NULL
                )
            );
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS idx_notification_logs_schedule
    ON public.notification_logs (delivery_status, scheduled_at);

CREATE TABLE IF NOT EXISTS public.master_customers (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.master_products (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.master_voc_types (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    voc_type text NOT NULL CHECK (btrim(voc_type) <> ''),
    voc_subtype text NOT NULL CHECK (btrim(voc_subtype) <> ''),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (voc_type, voc_subtype)
);

CREATE TABLE IF NOT EXISTS public.master_people (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    department text NOT NULL CHECK (btrim(department) <> ''),
    name text NOT NULL CHECK (btrim(name) <> ''),
    email text NOT NULL UNIQUE CHECK (btrim(email) <> ''),
    role text NOT NULL
        CHECK (role IN ('task_owner', 'department_manager', 'final_approver')),
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.master_final_approvers (
    singleton_id smallint PRIMARY KEY DEFAULT 1 CHECK (singleton_id = 1),
    person_id bigint NOT NULL
        REFERENCES public.master_people(id) ON DELETE RESTRICT,
    updated_by text NOT NULL CHECK (btrim(updated_by) <> ''),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.master_templates (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    template_key text NOT NULL UNIQUE CHECK (btrim(template_key) <> ''),
    subject_template text NOT NULL,
    body_template text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    updated_by text NOT NULL CHECK (btrim(updated_by) <> ''),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.master_notification_settings (
    singleton_id smallint PRIMARY KEY DEFAULT 1 CHECK (singleton_id = 1),
    weekday_time time NOT NULL DEFAULT '09:00',
    timezone_name text NOT NULL DEFAULT 'Asia/Seoul'
        CHECK (btrim(timezone_name) <> ''),
    updated_by text NOT NULL CHECK (btrim(updated_by) <> ''),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.reject_immutable_row_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION '% rows are immutable', TG_TABLE_NAME;
END;
$$;

DO $$
DECLARE
    immutable_table text;
BEGIN
    FOREACH immutable_table IN ARRAY ARRAY[
        'writer_attempts', 'task_reviews', 'voc_stage_history', 'change_audits'
    ]
    LOOP
        IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgrelid = format('public.%I', immutable_table)::regclass
              AND tgname = 'reject_immutable_row_change'
              AND NOT tgisinternal
        ) THEN
            EXECUTE format(
                'CREATE TRIGGER reject_immutable_row_change '
                'BEFORE UPDATE OR DELETE ON public.%I '
                'FOR EACH ROW EXECUTE FUNCTION public.reject_immutable_row_change()',
                immutable_table
            );
        END IF;
    END LOOP;
END;
$$;
