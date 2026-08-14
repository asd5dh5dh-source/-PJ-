\set ON_ERROR_STOP on
\encoding UTF8

SELECT datname
FROM pg_database
WHERE datname IN ('테스트용 Data', '학습용 Data')
ORDER BY datname;

\connect "테스트용 Data"
SELECT
    current_database() AS database_name,
    count(*) AS row_count,
    count(DISTINCT case_id) AS unique_case_ids,
    count(*) FILTER (WHERE customer_request_embedding IS NULL) AS null_request_vectors,
    count(*) FILTER (WHERE original_mail_body_embedding IS NULL) AS null_mail_vectors,
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_max_dims
FROM public.voc_cases;

\connect "학습용 Data"
SELECT
    current_database() AS database_name,
    count(*) AS row_count,
    count(DISTINCT case_id) AS unique_case_ids,
    count(*) FILTER (WHERE customer_request_embedding IS NULL) AS null_request_vectors,
    count(*) FILTER (WHERE original_mail_body_embedding IS NULL) AS null_mail_vectors,
    min(jsonb_array_length(customer_request_embedding::jsonb)) AS request_min_dims,
    max(jsonb_array_length(customer_request_embedding::jsonb)) AS request_max_dims,
    min(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_min_dims,
    max(jsonb_array_length(original_mail_body_embedding::jsonb)) AS mail_max_dims,
    count(*) FILTER (WHERE received_at IS NULL) AS null_received_dates,
    min(received_at) AS earliest_received_at,
    max(received_at) AS latest_received_at
FROM public.voc_cases;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'voc_cases'
  AND column_name IN (
      'received_at', 'first_response_at', 'containment_at',
      'root_cause_action_5d_at', 'customer_reply_at',
      'auto_close', 'reactivated', 'due_6d_at',
      'customer_request_embedding', 'original_mail_body_embedding'
  )
ORDER BY ordinal_position;
