\set ON_ERROR_STOP on
\encoding UTF8

SELECT format('CREATE DATABASE %I ENCODING %L', '테스트용 Data', 'UTF8')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '테스트용 Data')
\gexec

SELECT format('CREATE DATABASE %I ENCODING %L', '학습용 Data', 'UTF8')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '학습용 Data')
\gexec

\connect "테스트용 Data"

CREATE TABLE IF NOT EXISTS public.voc_cases (
    case_id text PRIMARY KEY,
    customer_name text,
    country text,
    voc_type text,
    voc_subtype text,
    priority text,
    customer_request text,
    original_mail_body text,
    responsible_departments text,
    received_at date,
    first_response_at date,
    containment_at date,
    root_cause_action_5d_at date,
    customer_reply_at date,
    final_status text,
    delay_stage text,
    delay_reason text,
    auto_close char(1),
    reactivated char(1),
    due_6d_at date,
    result_6d text,
    full_response_history text,
    customer_request_embedding text,
    original_mail_body_embedding text
);

CREATE TEMP TABLE voc_cases_import (LIKE public.voc_cases INCLUDING DEFAULTS);
\copy voc_cases_import FROM 'C:/Users/POSCOFUTUREM/Documents/Codex/2026-08-13/new-chat-3/work/voc_test.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO public.voc_cases
SELECT * FROM voc_cases_import WHERE true
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
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_max_dims
FROM public.voc_cases;

\connect "학습용 Data"

CREATE TABLE IF NOT EXISTS public.voc_cases (
    case_id text PRIMARY KEY,
    customer_name text,
    country text,
    voc_type text,
    voc_subtype text,
    priority text,
    customer_request text,
    original_mail_body text,
    responsible_departments text,
    received_at date,
    first_response_at date,
    containment_at date,
    root_cause_action_5d_at date,
    customer_reply_at date,
    final_status text,
    delay_stage text,
    delay_reason text,
    auto_close char(1),
    reactivated char(1),
    due_6d_at date,
    result_6d text,
    full_response_history text,
    customer_request_embedding text,
    original_mail_body_embedding text
);

CREATE TEMP TABLE voc_cases_import (LIKE public.voc_cases INCLUDING DEFAULTS);
\copy voc_cases_import FROM 'C:/Users/POSCOFUTUREM/Documents/Codex/2026-08-13/new-chat-3/work/voc_train.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')

INSERT INTO public.voc_cases
SELECT * FROM voc_cases_import WHERE true
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
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_vector_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_vector_max_dims
FROM public.voc_cases;
