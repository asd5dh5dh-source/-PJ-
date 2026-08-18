export type ArchiveSort = "relevance" | "latest" | "oldest";

export type ArchiveQuery = {
  q?: string;
  customer_name?: string;
  product_equipment?: string;
  voc_type?: string;
  voc_subtype?: string;
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
