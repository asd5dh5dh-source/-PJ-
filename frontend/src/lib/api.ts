import type {
  ArchiveDetail,
  ArchiveItem,
  ArchivePageData,
  ArchiveQuery,
  DashboardData,
  DashboardPeriod,
  DepartmentTask,
  MasterRecord,
  MasterResource,
  MailAnalysis,
  NotificationLog,
  TaskReview,
  VocCreateInput,
  VocDetail,
  VocRound,
  VocStage,
  WriterCredentials,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

function queryString(query: ArchiveQuery) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== 1) {
      params.set(key, String(value));
    }
  });
  return params.toString();
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { signal });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

function writerHeaders(writer: WriterCredentials) {
  return {
    "X-Writer-Name": encodeURIComponent(writer.writer_name),
    "X-Writer-Password": writer.password,
  };
}

async function postJson<T>(path: string, payload: unknown, writer?: WriterCredentials): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(writer ? writerHeaders(writer) : {}),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export function getArchive(query: ArchiveQuery, signal?: AbortSignal) {
  const search = queryString(query);
  return getJson<ArchivePageData>(`/api/archive${search ? `?${search}` : ""}`, signal);
}

export function analyzeMail(original_mail_body: string) {
  return postJson<MailAnalysis>("/api/mail-analysis", { original_mail_body });
}

export function getArchiveDetail(caseId: string, signal?: AbortSignal) {
  return getJson<ArchiveDetail>(`/api/archive/${encodeURIComponent(caseId)}`, signal);
}

export function getDashboard(
  query: { period?: DashboardPeriod; date_from?: string; date_to?: string },
  signal?: AbortSignal,
) {
  const search = new URLSearchParams(
    Object.entries(query).filter((entry): entry is [string, string] => Boolean(entry[1])),
  ).toString();
  return getJson<DashboardData>(`/api/dashboard?${search}`, signal);
}

export function getNotifications(signal?: AbortSignal) {
  return getJson<NotificationLog[]>("/api/notifications", signal);
}

export async function downloadArchive(
  format: "csv" | "xlsx",
  query: ArchiveQuery,
  writer: WriterCredentials,
) {
  const search = queryString(query);
  const response = await fetch(
    `${API_BASE_URL}/api/export/archive.${format}${search ? `?${search}` : ""}`,
    { headers: writerHeaders(writer) },
  );
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.blob();
}

export async function getMasterData(resource: MasterResource, writer: WriterCredentials) {
  const response = await fetch(`${API_BASE_URL}/api/admin/master-data/${resource}`, {
    headers: writerHeaders(writer),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<MasterRecord[]>;
}

export function createMasterData(
  resource: MasterResource,
  payload: Record<string, unknown>,
  writer: WriterCredentials,
) {
  return postJson<MasterRecord>(`/api/admin/master-data/${resource}`, payload, writer);
}

export type ManualRequestInput = {
  customer_name: string;
  product_equipment?: string;
  voc_type: string;
  voc_subtype: string;
  customer_request: string;
  original_mail_body: string;
  responsible_departments?: string;
};

export async function createManualRequest(payload: ManualRequestInput) {
  const response = await fetch(`${API_BASE_URL}/api/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<ArchiveDetail>;
}

export function getSimilarCases(caseId: string, signal?: AbortSignal) {
  return getJson<{ items: ArchiveItem[] }>(
    `/api/requests/${encodeURIComponent(caseId)}/similar-cases`,
    signal,
  );
}

export function verifyWriter(writer: WriterCredentials) {
  return postJson<{ writer_name: string }>("/api/writer/verify", writer);
}

export function createVoc(payload: VocCreateInput, writer: WriterCredentials) {
  return postJson<VocRound>("/api/voc", payload, writer);
}

export function getVoc(caseId: string, signal?: AbortSignal) {
  return getJson<VocDetail>(`/api/voc/${encodeURIComponent(caseId)}`, signal);
}

export function createVocRound(
  caseId: string,
  payload: Partial<VocCreateInput> & Pick<VocCreateInput, "customer_request">,
  writer: WriterCredentials,
) {
  return postJson<VocRound>(`/api/voc/${encodeURIComponent(caseId)}/rounds`, payload, writer);
}

export function updateDepartmentTask(
  taskId: number,
  payload: Partial<DepartmentTask>,
  writer: WriterCredentials,
) {
  return postJson<DepartmentTask>(`/api/tasks/${taskId}`, payload, writer);
}

export function reviewDepartmentTask(
  taskId: number,
  payload: Pick<TaskReview, "reviewer_role" | "decision"> & { comment?: string },
  writer: WriterCredentials,
) {
  return postJson<TaskReview>(`/api/tasks/${taskId}/review`, payload, writer);
}

export function changeVocStage(
  caseId: string,
  payload: { stage: VocStage; reason?: string; cancellation_reason?: string; deletion_reason?: string; ecm_link?: string },
  writer: WriterCredentials,
) {
  return postJson<VocRound>(`/api/voc/${encodeURIComponent(caseId)}/stage`, payload, writer);
}
