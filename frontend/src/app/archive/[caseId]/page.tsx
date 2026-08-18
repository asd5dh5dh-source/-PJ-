"use client";

import { use, useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getArchiveDetail } from "@/lib/api";
import type { ArchiveDetail } from "@/lib/types";

const ARCHIVE_ORIGIN = "http://archive.local";

export function safeArchiveReturnTo(value?: string) {
  if (!value?.startsWith("/") || value.startsWith("//")) return "/archive";
  try {
    const target = new URL(value, ARCHIVE_ORIGIN);
    if (target.origin !== ARCHIVE_ORIGIN || target.pathname !== "/archive") {
      return "/archive";
    }
    return `${target.pathname}${target.search}`;
  } catch {
    return "/archive";
  }
}

export function ArchiveDetailContent({
  caseId,
  returnTo,
}: {
  caseId: string;
  returnTo?: string;
}) {
  const [detail, setDetail] = useState<ArchiveDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    getArchiveDetail(caseId, controller.signal)
      .then(setDetail)
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setDetail(null);
          setError(true);
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [caseId, retry]);

  return (
    <AppShell>
      <div className="page-header">
        <p>VOC CASE</p>
        <h1>{caseId}</h1>
        <span>아카이브 사례의 원문과 전체 대응 이력을 확인합니다.</span>
      </div>
      {loading ? (
        <div className="state-panel" role="status">상세 정보를 불러오는 중입니다.</div>
      ) : error ? (
        <div className="state-panel" role="alert">
          <p>상세 정보를 불러오지 못했습니다.</p>
          <button className="secondary-button" type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button>
        </div>
      ) : detail ? (
        <article className="filter-panel preview-content">
          <dl className="preview-facts">
            <div><dt>고객사</dt><dd>{detail.customer_name ?? "—"}</dd></div>
            <div><dt>제품 / 설비</dt><dd>{detail.product_equipment ?? "—"}</dd></div>
            <div><dt>VOC 유형</dt><dd>{detail.voc_type ?? "—"} / {detail.voc_subtype ?? "—"}</dd></div>
            <div><dt>상태</dt><dd>{detail.final_status ?? "—"}</dd></div>
            <div><dt>담당 부서</dt><dd>{detail.responsible_departments ?? "—"}</dd></div>
            <div><dt>접수일</dt><dd>{detail.received_at ?? "—"}</dd></div>
          </dl>
          <section><h2>고객 요청</h2><p>{detail.customer_request ?? "내용 없음"}</p></section>
          <section><h2>원본 메일</h2><p className="preserve-lines">{detail.original_mail_body ?? "내용 없음"}</p></section>
          <section><h2>전체 대응 이력</h2><p className="preserve-lines">{detail.full_response_history ?? "내용 없음"}</p></section>
          <a className="primary-link" href={safeArchiveReturnTo(returnTo)}>검색 결과로 돌아가기</a>
        </article>
      ) : null}
    </AppShell>
  );
}

export default function ArchiveDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ caseId: string }>;
  searchParams: Promise<{ return_to?: string | string[] }>;
}) {
  const { caseId } = use(params);
  const { return_to: returnTo } = use(searchParams);
  return (
    <ArchiveDetailContent
      caseId={caseId}
      returnTo={typeof returnTo === "string" ? returnTo : undefined}
    />
  );
}
