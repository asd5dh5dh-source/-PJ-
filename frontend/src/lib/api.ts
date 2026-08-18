import type { ArchiveDetail, ArchivePageData, ArchiveQuery } from "./types";

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
