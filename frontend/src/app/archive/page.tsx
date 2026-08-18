"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import ArchiveFilters from "@/components/ArchiveFilters";
import ArchivePreview from "@/components/ArchivePreview";
import ArchiveResults from "@/components/ArchiveResults";
import { getArchive, getArchiveDetail } from "@/lib/api";
import type { ArchiveDetail, ArchivePageData, ArchiveQuery, ArchiveSort } from "@/lib/types";

const queryKeys = ["q", "customer_name", "product_equipment", "voc_type", "voc_subtype", "final_status", "responsible_department", "received_from", "received_to"] as const;

function readLocation(search: string) {
  const params = new URLSearchParams(search);
  const query: ArchiveQuery = {};
  queryKeys.forEach((key) => {
    const value = params.get(key)?.trim();
    if (value) query[key] = value;
  });
  const sort = params.get("sort");
  if (sort === "relevance" || sort === "latest" || sort === "oldest") query.sort = sort as ArchiveSort;
  const page = Number(params.get("page"));
  if (Number.isInteger(page) && page > 1) query.page = page;
  return { query, caseId: params.get("case_id") ?? undefined };
}

function serialize(query: ArchiveQuery, caseId?: string) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== 1) params.set(key, String(value));
  });
  if (caseId) params.set("case_id", caseId);
  return params.toString();
}

export default function ArchivePage() {
  const [locationSearch, setLocationSearch] = useState("");
  const [data, setData] = useState<ArchivePageData | null>(null);
  const [detail, setDetail] = useState<ArchiveDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const [retry, setRetry] = useState(0);
  const [detailRetry, setDetailRetry] = useState(0);

  useEffect(() => {
    const sync = () => setLocationSearch(window.location.search);
    sync();
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const { query, caseId } = useMemo(() => readLocation(locationSearch), [locationSearch]);
  const listKey = useMemo(() => serialize(query), [query]);

  const navigate = useCallback((nextQuery: ArchiveQuery, nextCaseId?: string) => {
    const search = serialize(nextQuery, nextCaseId);
    const url = `/archive${search ? `?${search}` : ""}`;
    window.history.pushState({}, "", url);
    setLocationSearch(window.location.search);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    getArchive(query, controller.signal).then(setData).catch((requestError: unknown) => {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
        setData(null);
        setError(true);
      }
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [listKey, retry]);

  useEffect(() => {
    if (!caseId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    setDetail(null);
    setDetailLoading(true);
    setDetailError(false);
    getArchiveDetail(caseId, controller.signal).then(setDetail).catch((requestError: unknown) => {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setDetailError(true);
    }).finally(() => {
      if (!controller.signal.aborted) setDetailLoading(false);
    });
    return () => controller.abort();
  }, [caseId, detailRetry]);

  const returnTo = `/archive${listKey ? `?${listKey}` : ""}`;

  return (
    <AppShell>
      <div className="page-header"><p>VOC ARCHIVE</p><h1>고객 VOC 아카이브</h1><span>과거 사례를 검색하고 원문과 대응 이력을 한 화면에서 확인합니다.</span></div>
      <ArchiveFilters query={query} onApply={(next) => navigate({ ...next, page: undefined })} />
      <div className={`archive-layout${caseId ? " has-preview" : ""}`}>
        <ArchiveResults
          data={data}
          loading={loading}
          error={error}
          selectedCaseId={caseId}
          onSelect={(selected) => navigate(query, selected)}
          onPage={(page) => navigate({ ...query, page }, caseId)}
          onRetry={() => setRetry((value) => value + 1)}
        />
        {caseId && (
          <ArchivePreview
            caseId={caseId}
            detail={detail}
            loading={detailLoading}
            error={detailError}
            returnTo={returnTo}
            onClose={() => navigate(query)}
            onRetry={() => setDetailRetry((value) => value + 1)}
          />
        )}
      </div>
    </AppShell>
  );
}
