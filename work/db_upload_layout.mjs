export const DB_HEADERS = [
  "case_id",
  "customer_name",
  "country",
  "voc_type",
  "voc_subtype",
  "priority",
  "customer_request",
  "original_mail_body",
  "responsible_departments",
  "received_at",
  "first_response_at",
  "containment_at",
  "root_cause_action_5d_at",
  "customer_reply_at",
  "final_status",
  "delay_stage",
  "delay_reason",
  "auto_close",
  "reactivated",
  "due_6d_at",
  "result_6d",
  "full_response_history",
  "customer_request_embedding",
  "original_mail_body_embedding",
];

export function toUploadRows(rows) {
  return [DB_HEADERS, ...rows.slice(1).filter((row) => row[0])];
}
