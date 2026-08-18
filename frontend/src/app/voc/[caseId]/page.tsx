"use client";

import { use, useEffect, useState } from "react";
import type { FormEvent } from "react";

import ApprovalPanel from "@/components/ApprovalPanel";
import AppShell from "@/components/AppShell";
import DepartmentTaskBoard from "@/components/DepartmentTaskBoard";
import VocTimeline, { stageLabels } from "@/components/VocTimeline";
import WriterGate from "@/components/WriterGate";
import type { RequestWriter } from "@/components/WriterGate";
import { changeVocStage, createVocRound, getVoc } from "@/lib/api";
import type { VocDetail, VocStage } from "@/lib/types";

function value(values: FormData, name: string) {
  return String(values.get(name) ?? "").trim();
}

export function VocDetailContent({ caseId }: { caseId: string }) {
  const [detail, setDetail] = useState<VocDetail>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [stageForm, setStageForm] = useState({ stage: "received" as VocStage, reason: "", ecm_link: "" });

  async function refresh() {
    setDetail(await getVoc(caseId));
  }

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getVoc(caseId, controller.signal)
      .then(setDetail)
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setError("VOC 상세 정보를 불러오지 못했습니다.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [caseId, retry]);

  function changeStage(event: FormEvent<HTMLFormElement>, requestWriter: RequestWriter) {
    event.preventDefault();
    const { stage, ecm_link } = stageForm;
    const reason = stageForm.reason.trim();
    requestWriter(async (writer) => {
      setError("");
      try {
        await changeVocStage(caseId, {
          stage,
          reason: reason || undefined,
          cancellation_reason: stage === "cancelled" ? reason || undefined : undefined,
          deletion_reason: stage === "deleted" ? reason || undefined : undefined,
          ecm_link: ecm_link.trim() || undefined,
        }, writer);
        await refresh();
      } catch {
        setError("전체 단계를 변경하지 못했습니다. 전환 조건과 승인 상태를 확인해 주세요.");
      }
    });
  }

  function addRound(event: FormEvent<HTMLFormElement>, requestWriter: RequestWriter) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const customer_request = value(values, "customer_request");
    if (!customer_request) {
      setError("추가 고객 요청을 입력해 주세요.");
      return;
    }
    requestWriter(async (writer) => {
      setError("");
      try {
        await createVocRound(caseId, {
          customer_request,
          original_mail_body: value(values, "original_mail_body"),
        }, writer);
        await refresh();
      } catch {
        setError("요청 라운드를 추가하지 못했습니다.");
      }
    });
  }

  const latest = detail?.rounds.at(-1);
  useEffect(() => {
    if (latest) setStageForm({ stage: latest.stage, reason: "", ecm_link: "" });
  }, [latest]);

  return (
    <AppShell activeSection="voc">
      <div className="page-header">
        <p>VOC MANAGEMENT</p>
        <h1>{caseId}</h1>
        <span>{latest ? `전체 단계: ${stageLabels[latest.stage]}` : "요청 라운드와 부서 과제를 불러옵니다."}</span>
      </div>
      {loading ? (
        <div className="state-panel" role="status">VOC 상세 정보를 불러오는 중입니다.</div>
      ) : !detail || !latest ? (
        <div className="state-panel" role="alert"><p>{error || "VOC를 찾을 수 없습니다."}</p><button className="secondary-button" type="button" onClick={() => setRetry((count) => count + 1)}>다시 시도</button></div>
      ) : (
        <WriterGate>
          {(requestWriter) => (
            <>
              <section className="filter-panel preview-content" aria-labelledby="voc-summary-heading">
                <h2 id="voc-summary-heading">현재 요청</h2>
                <dl className="preview-facts">
                  <div><dt>발신자</dt><dd>{latest.sender_name || "—"} {latest.sender_email && `<${latest.sender_email}>`}</dd></div>
                  <div><dt>회사</dt><dd>{latest.sender_company || "—"}</dd></div>
                  <div><dt>VOC</dt><dd>{latest.voc_type || "—"} / {latest.voc_subtype || "—"}</dd></div>
                  <div><dt>제품 / 설비</dt><dd>{latest.product_equipment || "—"}</dd></div>
                  <div><dt>우선순위</dt><dd>{latest.priority === "high" ? "높음" : "일반"}</dd></div>
                </dl>
              </section>
              <VocTimeline rounds={detail.rounds} />
              <DepartmentTaskBoard tasks={latest.tasks} requestWriter={requestWriter} onChanged={refresh} />
              <ApprovalPanel tasks={latest.tasks} reviews={latest.reviews} requestWriter={requestWriter} onChanged={refresh} />
              <section className="filter-panel" aria-labelledby="stage-action-heading">
                <h2 id="stage-action-heading">전체 단계 변경</h2>
                <form onSubmit={(event) => changeStage(event, requestWriter)}>
                  <div className="filter-grid">
                    <label><span>전체 단계</span><select name="stage" value={stageForm.stage} onChange={(event) => setStageForm((current) => ({ ...current, stage: event.target.value as VocStage }))}>{Object.entries(stageLabels).map(([stage, label]) => <option key={stage} value={stage}>{label}</option>)}</select></label>
                    <label><span>변경 / 취소 / 삭제 사유</span><input name="reason" value={stageForm.reason} onChange={(event) => setStageForm((current) => ({ ...current, reason: event.target.value }))} /></label>
                    <label><span>ECM 링크</span><input name="ecm_link" type="url" value={stageForm.ecm_link} onChange={(event) => setStageForm((current) => ({ ...current, ecm_link: event.target.value }))} /></label>
                  </div>
                  <button className="primary-button" type="submit">단계 변경</button>
                </form>
              </section>
              {(latest.stage === "customer_reply" || latest.stage === "completed") && (
                <section className="filter-panel" aria-labelledby="round-action-heading">
                  <h2 id="round-action-heading">추가 요청 라운드</h2>
                  <form onSubmit={(event) => addRound(event, requestWriter)}>
                    <label className="search-field"><span>추가 고객 요청</span><textarea name="customer_request" rows={3} /></label>
                    <label className="search-field"><span>추가 원본 메일</span><textarea name="original_mail_body" rows={5} /></label>
                    <button className="primary-button" type="submit">새 라운드 만들기</button>
                  </form>
                </section>
              )}
              <section className="filter-panel" aria-labelledby="audit-heading">
                <h2 id="audit-heading">변경 감사 이력</h2>
                <ol className="audit-list">
                  {detail.audits.map((audit) => (
                    <li key={audit.id}><strong>{audit.writer_name} · {audit.action}</strong><span>{audit.entity_type} #{audit.entity_id} · {new Date(audit.changed_at).toLocaleString("ko-KR")}</span></li>
                  ))}
                </ol>
              </section>
              {error && <p className="state-panel" role="alert">{error}</p>}
            </>
          )}
        </WriterGate>
      )}
    </AppShell>
  );
}

export default function VocDetailPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = use(params);
  return <VocDetailContent caseId={caseId} />;
}
