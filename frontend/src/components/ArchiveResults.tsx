import type { ArchivePageData } from "@/lib/types";

function text(value: string | number | null) {
  return value === null || value === "" ? "—" : value;
}

const statusLabel: Record<string, string> = {
  received: "요청 접수",
  managing: "대응 중",
  in_progress: "대응 중",
  department_work: "부서별 검토 요청",
  department_review: "부서 검토",
  manager_review: "직책자 검토",
  final_review: "최종 승인 검토",
  customer_reply: "고객 회신",
  completed: "완료",
};

export default function ArchiveResults({
  data,
  loading,
  error,
  selectedCaseId,
  onSelect,
  onPage,
  onRetry,
}: {
  data: ArchivePageData | null;
  loading: boolean;
  error: boolean;
  selectedCaseId?: string;
  onSelect: (caseId: string) => void;
  onPage: (page: number) => void;
  onRetry: () => void;
}) {
  if (loading) return <div className="state-panel" role="status">검색 결과를 불러오는 중입니다.</div>;
  if (error) {
    return (
      <div className="state-panel error-state" role="alert">
        <p>검색 결과를 불러오지 못했습니다.</p>
        <button className="secondary-button" type="button" onClick={onRetry}>다시 시도</button>
      </div>
    );
  }
  if (!data?.items.length) return <div className="state-panel">조건에 맞는 VOC 사례가 없습니다.</div>;

  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <section className="results-panel" aria-labelledby="results-heading">
      <div className="results-heading">
        <div>
          <h2 id="results-heading">검색 결과</h2>
          <p>총 {data.total.toLocaleString("ko-KR")}건 · 페이지당 {data.page_size}건</p>
        </div>
        <span>{data.sort === "relevance" ? "관련도순" : data.sort === "oldest" ? "오래된순" : "최신순"}</span>
      </div>
      <div className="table-scroll" tabIndex={0} aria-label="검색 결과 표 가로 스크롤 영역">
        <table>
          <thead>
            <tr>
              <th>Case ID</th><th>고객사</th><th>제품 / 설비</th><th>VOC 유형 / 세부</th>
              <th>요청 요약</th><th>담당 부서</th><th>상태</th><th>접수일</th><th>점수</th><th>일치 키워드</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.case_id} data-testid="archive-result" className={selectedCaseId === item.case_id ? "selected-row" : undefined}>
                <td>{item.record_origin === "current" ? <a className="case-link" href={`/voc/${encodeURIComponent(item.case_id)}`} aria-label={`${item.case_id} 관리 화면`}>{item.case_id}</a> : <button className="case-link" type="button" onClick={() => onSelect(item.case_id)} aria-pressed={selectedCaseId === item.case_id}>{item.case_id}</button>}</td>
                <td>{text(item.customer_name)}</td>
                <td>{text(item.product_equipment)}</td>
                <td>{text(item.voc_type)}<small>{text(item.voc_subtype)}</small></td>
                <td className="summary-cell">{text(item.customer_request)}</td>
                <td>{text(item.responsible_departments)}</td>
                <td><span className="status-badge">{item.final_status ? statusLabel[item.final_status] ?? item.final_status : "—"}</span></td>
                <td>{text(item.received_at)}</td>
                <td>{text(item.final_score ?? item.bm25_score)}</td>
                <td><div className="keyword-list">{item.matched_keywords.length ? item.matched_keywords.map((keyword) => <span key={keyword}>{keyword}</span>) : "—"}</div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="pagination" aria-label="검색 결과 페이지">
        <button type="button" disabled={data.page <= 1} onClick={() => onPage(data.page - 1)}>이전</button>
        <span>{data.page} / {lastPage}</span>
        <button type="button" disabled={data.page >= lastPage} onClick={() => onPage(data.page + 1)}>다음</button>
      </nav>
    </section>
  );
}
