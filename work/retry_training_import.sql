\set ON_ERROR_STOP on
\encoding UTF8

\connect "테스트용 Data"

ALTER TABLE public.voc_cases
    ALTER COLUMN containment_at TYPE text USING containment_at::text,
    ALTER COLUMN root_cause_action_5d_at TYPE text USING root_cause_action_5d_at::text,
    ALTER COLUMN customer_reply_at TYPE text USING customer_reply_at::text,
    ALTER COLUMN auto_close TYPE boolean USING CASE
        WHEN upper(auto_close) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(auto_close) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END,
    ALTER COLUMN reactivated TYPE boolean USING CASE
        WHEN upper(reactivated) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(reactivated) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END;

SELECT
    current_database() AS database_name,
    count(*) AS row_count,
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_max_dims
FROM public.voc_cases;

\connect "학습용 Data"

ALTER TABLE public.voc_cases
    ALTER COLUMN containment_at TYPE text USING containment_at::text,
    ALTER COLUMN root_cause_action_5d_at TYPE text USING root_cause_action_5d_at::text,
    ALTER COLUMN customer_reply_at TYPE text USING customer_reply_at::text,
    ALTER COLUMN auto_close TYPE boolean USING CASE
        WHEN upper(auto_close) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(auto_close) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END,
    ALTER COLUMN reactivated TYPE boolean USING CASE
        WHEN upper(reactivated) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(reactivated) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END;

CREATE TEMP TABLE voc_cases_import_raw (LIKE public.voc_cases INCLUDING DEFAULTS);
ALTER TABLE voc_cases_import_raw
    ALTER COLUMN received_at TYPE text USING received_at::text,
    ALTER COLUMN first_response_at TYPE text USING first_response_at::text,
    ALTER COLUMN due_6d_at TYPE text USING due_6d_at::text,
    ALTER COLUMN auto_close TYPE text USING auto_close::text,
    ALTER COLUMN reactivated TYPE text USING reactivated::text;

\copy voc_cases_import_raw FROM 'C:/Users/POSCOFUTUREM/Documents/Codex/2026-08-13/new-chat-3/work/voc_train.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO public.voc_cases (
    case_id, customer_name, country, voc_type, voc_subtype, priority,
    customer_request, original_mail_body, responsible_departments,
    received_at, first_response_at, containment_at, root_cause_action_5d_at,
    customer_reply_at, final_status, delay_stage, delay_reason, auto_close,
    reactivated, due_6d_at, result_6d, full_response_history,
    customer_request_embedding, original_mail_body_embedding
)
SELECT
    case_id, customer_name, country, voc_type, voc_subtype, priority,
    customer_request, original_mail_body, responsible_departments,
    CASE
        WHEN received_at ~ '^\d{4}-\d{2}-\d{2}$' THEN received_at::date
        WHEN received_at ~ '^\d+$' THEN DATE '1899-12-30' + received_at::integer
        ELSE NULL
    END,
    CASE
        WHEN first_response_at ~ '^\d{4}-\d{2}-\d{2}$' THEN first_response_at::date
        WHEN first_response_at ~ '^\d+$' THEN DATE '1899-12-30' + first_response_at::integer
        ELSE NULL
    END,
    containment_at, root_cause_action_5d_at, customer_reply_at,
    final_status, delay_stage, delay_reason,
    CASE
        WHEN upper(auto_close) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(auto_close) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END,
    CASE
        WHEN upper(reactivated) IN ('Y', 'TRUE', 'T', '1') THEN true
        WHEN upper(reactivated) IN ('N', 'FALSE', 'F', '0') THEN false
        ELSE NULL
    END,
    CASE
        WHEN due_6d_at ~ '^\d{4}-\d{2}-\d{2}$' THEN due_6d_at::date
        WHEN due_6d_at ~ '^\d+$' THEN DATE '1899-12-30' + due_6d_at::integer
        ELSE NULL
    END,
    result_6d, full_response_history,
    customer_request_embedding, original_mail_body_embedding
FROM voc_cases_import_raw
WHERE true
ON CONFLICT (case_id) DO UPDATE SET
    customer_name = EXCLUDED.customer_name,
    country = EXCLUDED.country,
    voc_type = EXCLUDED.voc_type,
    voc_subtype = EXCLUDED.voc_subtype,
    priority = EXCLUDED.priority,
    customer_request = EXCLUDED.customer_request,
    original_mail_body = EXCLUDED.original_mail_body,
    responsible_departments = EXCLUDED.responsible_departments,
    received_at = EXCLUDED.received_at,
    first_response_at = EXCLUDED.first_response_at,
    containment_at = EXCLUDED.containment_at,
    root_cause_action_5d_at = EXCLUDED.root_cause_action_5d_at,
    customer_reply_at = EXCLUDED.customer_reply_at,
    final_status = EXCLUDED.final_status,
    delay_stage = EXCLUDED.delay_stage,
    delay_reason = EXCLUDED.delay_reason,
    auto_close = EXCLUDED.auto_close,
    reactivated = EXCLUDED.reactivated,
    due_6d_at = EXCLUDED.due_6d_at,
    result_6d = EXCLUDED.result_6d,
    full_response_history = EXCLUDED.full_response_history,
    customer_request_embedding = EXCLUDED.customer_request_embedding,
    original_mail_body_embedding = EXCLUDED.original_mail_body_embedding;

SELECT
    current_database() AS database_name,
    count(*) AS row_count,
    count(DISTINCT case_id) AS unique_case_ids,
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_max_dims,
    count(*) FILTER (WHERE received_at IS NULL) AS missing_received_dates
FROM public.voc_cases;
