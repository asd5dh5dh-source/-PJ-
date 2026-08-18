"use client";

import { useEffect, useState } from "react";

import { getSimilarCases } from "@/lib/api";
import type { ArchiveItem } from "@/lib/types";

function text(value: string | number | null) {
  return value === null || value === "" ? "—" : value;
}

function score(value: number | null) {
  return value === null ? "—" : value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

export default function SimilarCases({ caseId }: { caseId: string }) {
  const [items, setItems] = useState<ArchiveItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    getSimilarCases(caseId, controller.signal).then((data) => {
      setItems(data.items.slice(0, 3));
    }).catch((requestError: unknown) => {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(true);
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [caseId, retry]);

  if (loading) return <div className="state-panel" role="status">저장했습니다. 유사한 종료 사례를 찾는 중입니다.</div>;
  if (error) {
    return (
      <div className="state-panel" role="alert">
        <p>저장했지만 유사 사례를 불러오지 못했습니다.</p>
        <button className="secondary-button" type="button" onClick={() => setRetry((value) => value + 1)}>다시 시도</button>
      </div>
    );
  }

  return (
    <section aria-labelledby="similar-cases-heading">
      <div className="page-header">
        <p>TOP 3</p>
        <h2 id="similar-cases-heading">유사한 종료 사례</h2>
        <span>저장된 요청과 가장 가까운 종료 사례입니다.</span>
      </div>
      {items.length === 0 && <div className="state-panel">유사한 종료 사례가 없습니다.</div>}
      {items.map((item) => (
        <article className="filter-panel" data-testid="similar-case" key={item.case_id}>
          <div className="results-heading">
            <div><h3>{item.case_id}</h3><p>상대 점수 {score(item.final_score ?? item.bm25_score)}</p></div>
            <span>{text(item.final_status)}</span>
          </div>
          <div className="preview-content">
            <dl className="preview-facts">
              <div><dt>일치 키워드</dt><dd><span className="keyword-list">{item.matched_keywords.length ? item.matched_keywords.map((keyword) => <span key={keyword}>{keyword}</span>) : "—"}</span></dd></div>
              <div><dt>고객</dt><dd>{text(item.customer_name)}</dd></div>
              <div><dt>제품 / 설비</dt><dd>{text(item.product_equipment)}</dd></div>
              <div><dt>VOC</dt><dd>{text(item.voc_type)} / {text(item.voc_subtype)}</dd></div>
              <div><dt>요청 요약</dt><dd>{text(item.customer_request)}</dd></div>
              <div><dt>담당 부서</dt><dd>{text(item.responsible_departments)}</dd></div>
              <div><dt>접수일</dt><dd>{text(item.received_at)}</dd></div>
            </dl>
            <a className="primary-link" href={`/archive?case_id=${encodeURIComponent(item.case_id)}`} aria-label={`${item.case_id} 상세 보기`}>아카이브 상세 보기</a>
          </div>
        </article>
      ))}
    </section>
  );
}
