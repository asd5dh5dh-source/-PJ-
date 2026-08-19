export type ArchiveSort = "relevance" | "latest" | "oldest";

export type ArchiveQuery = {
  q?: string;
  customer_name?: string;
  product_equipment?: string;
  voc_type?: string;
  voc_subtype?: string;
  boost_voc_subtype?: string;
  final_status?: string;
  responsible_department?: string;
  received_from?: string;
  received_to?: string;
  sort?: ArchiveSort;
  page?: number;
};

export type ArchiveItem = {
  case_id: string;
  customer_name: string | null;
  product_equipment: string | null;
  voc_type: string | null;
  voc_subtype: string | null;
  customer_request: string | null;
  responsible_departments: string | null;
  received_at: string | null;
  final_status: string | null;
  record_origin: string | null;
  bm25_score: number | null;
  final_score: number | null;
  matched_keywords: string[];
};

export type ArchiveDetail = ArchiveItem & {
  original_mail_body: string | null;
  full_response_history: string | null;
};

export type ArchivePageData = {
  items: ArchiveItem[];
  total: number;
  page: number;
  page_size: number;
  sort: ArchiveSort;
};

export type WriterCredentials = {
  writer_name: string;
  password: string;
};

export type DashboardPeriod = "30d" | "week" | "month";

export type DashboardData = {
  stage_counts: Array<{ stage: VocStage; count: number }>;
  due_tasks: Array<{
    id: number;
    case_id?: string | null;
    department?: string | null;
    status: TaskStatus;
    due_date?: string | null;
    priority?: "normal" | "high" | null;
    stage?: VocStage | null;
  }>;
  recent_requests: Array<{
    case_id: string;
    sender_company?: string | null;
    product_equipment?: string | null;
    priority?: "normal" | "high" | null;
    stage?: VocStage | null;
    created_at?: string | null;
  }>;
  active_requests: Array<{
    case_id: string;
    sender_company?: string | null;
    product_equipment?: string | null;
    voc_type?: string | null;
    voc_subtype?: string | null;
    responsible_departments?: string | null;
    priority?: "normal" | "high" | null;
    stage?: VocStage | null;
    created_at?: string | null;
  }>;
};

export type MailAnalysis = {
  sender_name?: string | null;
  sender_email?: string | null;
  sender_company?: string | null;
  translation_draft?: string | null;
  translation_status: string;
  suggested_voc_type?: string | null;
  suggested_voc_subtype?: string | null;
  suggested_product_equipment?: string | null;
  items: ArchiveItem[];
};

export type NotificationLog = {
  id: number;
  subject: string;
  body: string;
  scheduled_at?: string | null;
  sent_at?: string | null;
  runtime_profile: "external_review" | "internal";
  delivery_status: "preview" | "pending" | "sent" | "failed";
  real_delivery: boolean;
  created_at: string;
};

export type MasterResource =
  | "customers"
  | "products"
  | "voc_types"
  | "people"
  | "final_approver"
  | "templates"
  | "notification_settings";

export type MasterRecord = Record<string, unknown> & { id?: number; singleton_id?: number };

export type TaskStatus =
  | "not_started"
  | "reviewing"
  | "in_progress"
  | "completed"
  | "delayed"
  | "excluded";

export type VocStage =
  | "received"
  | "managing"
  | "in_progress"
  | "department_work"
  | "department_review"
  | "manager_review"
  | "final_review"
  | "customer_reply"
  | "completed"
  | "cancelled"
  | "deleted";

export type DepartmentTaskInput = {
  department: string;
  assignee_name?: string;
  assignee_email?: string;
  manager_name?: string;
  manager_email?: string;
  due_date?: string;
  ecm_link?: string;
};

export type DepartmentTask = DepartmentTaskInput & {
  id: number;
  voc_request_id: number;
  status: TaskStatus;
  response_content?: string | null;
  delay_reason?: string | null;
  revision?: number;
};

export type TaskReview = {
  id: number;
  voc_request_id: number;
  task_id: number | null;
  reviewer_role: "department_manager" | "final_approver";
  decision: "approved" | "rejected";
  task_revision?: number | null;
  comment?: string | null;
  reviewed_by?: string;
  reviewed_at?: string;
};

export type VocStageHistory = {
  id: number;
  voc_request_id: number;
  from_stage?: VocStage | null;
  to_stage: VocStage;
  reason?: string | null;
  ecm_link?: string | null;
  changed_by: string;
  changed_at: string;
};

export type VocRound = {
  id: number;
  case_id: string;
  round_number: number;
  customer_request: string;
  original_mail_body: string;
  sender_name?: string | null;
  sender_email?: string | null;
  sender_company?: string | null;
  translation_draft?: string | null;
  translation_final?: string | null;
  voc_type?: string | null;
  voc_subtype?: string | null;
  product_equipment?: string | null;
  priority: "normal" | "high";
  stage: VocStage;
  cancellation_reason?: string | null;
  deletion_reason?: string | null;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
  tasks: DepartmentTask[];
  reviews: TaskReview[];
  stage_history: VocStageHistory[];
};

export type ChangeAudit = {
  id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  writer_name: string;
  changed_at: string;
  before_values?: unknown;
  after_values?: unknown;
};

export type VocDetail = {
  case_id: string;
  rounds: VocRound[];
  audits: ChangeAudit[];
};

export type VocCreateInput = {
  customer_request: string;
  original_mail_body: string;
  sender_name?: string;
  sender_email?: string;
  sender_company?: string;
  translation_draft?: string;
  translation_final?: string;
  voc_type?: string;
  voc_subtype?: string;
  product_equipment?: string;
  priority: "normal" | "high";
  tasks: DepartmentTaskInput[];
};
