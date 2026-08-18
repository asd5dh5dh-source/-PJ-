import type { ArchiveDetail, ArchiveItem, ArchivePageData, ArchiveQuery } from "./types";

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

export function getArchive(query: ArchiveQuery, signal?: AbortSignal) {
  const search = queryString(query);
  return getJson<ArchivePageData>(`/api/archive${search ? `?${search}` : ""}`, signal);
}

export function getArchiveDetail(caseId: string, signal?: AbortSignal) {
  return getJson<ArchiveDetail>(`/api/archive/${encodeURIComponent(caseId)}`, signal);
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
