import type { ArchiveDetail } from "@/lib/types";

export default function ArchivePreview({
  caseId,
  detail,
  loading,
  error,
  returnTo,
  onClose,
  onRetry,
}: {
  caseId: string;
  detail: ArchiveDetail | null;
  loading: boolean;
  error: boolean;
  returnTo: string;
  onClose: () => void;
  onRetry: () => void;
}) {
  return (
    <aside className="preview-panel" aria-label={`${caseId} 사례 미리보기`}>
      <header>
        <div><span>CASE PREVIEW</span><h2>{caseId}</h2></div>
        <button className="icon-button" type="button" aria-label="미리보기 닫기" onClick={onClose}>×</button>
      </header>
      {loading ? <p role="status">상세 정보를 불러오는 중입니다.</p> : error ? (
        <div role="alert"><p>상세 정보를 불러오지 못했습니다.</p><button className="secondary-button" type="button" onClick={onRetry}>다시 시도</button></div>
      ) : detail ? (
        <div className="preview-content">
          <dl className="preview-facts">
            <div><dt>고객사</dt><dd>{detail.customer_name ?? "—"}</dd></div>
            <div><dt>제품 / 설비</dt><dd>{detail.product_equipment ?? "—"}</dd></div>
            <div><dt>VOC 유형</dt><dd>{detail.voc_type ?? "—"} / {detail.voc_subtype ?? "—"}</dd></div>
            <div><dt>상태</dt><dd>{detail.final_status ?? "—"}</dd></div>
            <div><dt>담당 부서</dt><dd>{detail.responsible_departments ?? "—"}</dd></div>
            <div><dt>접수일</dt><dd>{detail.received_at ?? "—"}</dd></div>
          </dl>
          <section><h3>고객 요청</h3><p>{detail.customer_request ?? "내용 없음"}</p></section>
          <section><h3>원본 메일</h3><p className="preserve-lines">{detail.original_mail_body ?? "내용 없음"}</p></section>
          <section><h3>전체 대응 이력</h3><p className="preserve-lines">{detail.full_response_history ?? "내용 없음"}</p></section>
          <a className="primary-link" href={`/archive/${encodeURIComponent(caseId)}?return_to=${encodeURIComponent(returnTo)}`}>상세 화면에서 보기</a>
        </div>
      ) : null}
    </aside>
  );
}
