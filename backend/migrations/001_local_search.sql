ALTER TABLE public.voc_cases
    ADD COLUMN IF NOT EXISTS product_equipment text,
    ADD COLUMN IF NOT EXISTS record_origin text NOT NULL DEFAULT 'historical',
    ADD COLUMN IF NOT EXISTS search_document text;

UPDATE public.voc_cases
SET record_origin = 'historical'
WHERE record_origin IS NULL OR record_origin = '';

UPDATE public.voc_cases
SET search_document = concat_ws(' ', customer_request, original_mail_body, full_response_history)
WHERE search_document IS NULL;

UPDATE public.voc_cases
SET product_equipment = substring(customer_request from '(?i)(NCM811|NCM9|NCA|LMFP|LFP)')
WHERE product_equipment IS NULL OR btrim(product_equipment) = '';

CREATE INDEX IF NOT EXISTS idx_voc_cases_received_at ON public.voc_cases (received_at DESC);
CREATE INDEX IF NOT EXISTS idx_voc_cases_filters ON public.voc_cases (voc_type, voc_subtype, final_status);
