"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import AppShell from "@/components/AppShell";
import WriterGate from "@/components/WriterGate";
import type { RequestWriter } from "@/components/WriterGate";
import { createVoc, getArchive } from "@/lib/api";
import type { ArchiveItem, VocCreateInput, WriterCredentials } from "@/lib/types";

function parseMail(mail: string) {
  const sender = mail.match(/^From:\s*(.*?)\s*<([^>]+)>\s*$/im);
  const company = mail.match(/^Company:\s*(.+?)\s*$/im);
  return {
    sender_name: sender?.[1]?.trim() ?? "",
    sender_email: sender?.[2]?.trim() ?? "",
    sender_company: company?.[1]?.trim() ?? "",
  };
}

function field(values: FormData, name: string) {
  return String(values.get(name) ?? "").trim();
}

function optional(value: string) {
  return value || undefined;
}

export default function NewRequestPage() {
  const formRef = useRef<HTMLFormElement>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [parsed, setParsed] = useState({ sender_name: "", sender_email: "", sender_company: "" });
  const [taskCount, setTaskCount] = useState(1);
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [saveError, setSaveError] = useState(false);
  const [similarError, setSimilarError] = useState(false);
  const [savedCaseId, setSavedCaseId] = useState("");
  const [similar, setSimilar] = useState<ArchiveItem[]>([]);
  const [searchText, setSearchText] = useState("");

  function analyzeMail() {
    const mail = formRef.current?.elements.namedItem("original_mail_body");
    if (!(mail instanceof HTMLTextAreaElement) || !mail.value.trim()) {
      setValidationError("원본 메일을 입력해 주세요.");
      return;
    }
    setParsed(parseMail(mail.value));
    setValidationError("");
    setConfirmed(true);
  }

  async function loadSimilar(query: string) {
    setSimilarError(false);
    try {
      const page = await getArchive({ q: query, final_status: "closed", sort: "relevance" });
      setSimilar(page.items.slice(0, 3));
    } catch {
      setSimilarError(true);
    }
  }

  async function save(payload: VocCreateInput, writer: WriterCredentials) {
    setSaving(true);
    setSaveError(false);
    setSimilarError(false);
    try {
      const created = await createVoc(payload, writer);
      setSavedCaseId(created.case_id);
      setSearchText(payload.customer_request);
      await loadSimilar(payload.customer_request);
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>, requestWriter: RequestWriter) {
    event.preventDefault();
    if (saving) return;
    const values = new FormData(event.currentTarget);
    const customerRequest = field(values, "customer_request");
    const vocType = field(values, "voc_type");
    const vocSubtype = field(values, "voc_subtype");
    if (!customerRequest || !vocType || !vocSubtype) {
      setValidationError(!customerRequest ? "고객 요청을 입력해 주세요." : "VOC 유형과 세부 유형을 확인해 주세요.");
      return;
    }
    const tasks = Array.from({ length: taskCount }, (_, index) => ({
      department: field(values, `task_department_${index}`),
      assignee_name: optional(field(values, `task_assignee_${index}`)),
      assignee_email: optional(field(values, `task_assignee_email_${index}`)),
      manager_name: optional(field(values, `task_manager_${index}`)),
      manager_email: optional(field(values, `task_manager_email_${index}`)),
      due_date: optional(field(values, `task_due_${index}`)),
      ecm_link: optional(field(values, `task_ecm_${index}`)),
    })).filter((task) => task.department);
    const payload: VocCreateInput = {
      customer_request: customerRequest,
      original_mail_body: field(values, "original_mail_body"),
      sender_name: optional(field(values, "sender_name")),
      sender_email: optional(field(values, "sender_email")),
      sender_company: optional(field(values, "sender_company")),
      voc_type: vocType,
      voc_subtype: vocSubtype,
      product_equipment: optional(field(values, "product_equipment")),
      priority: field(values, "priority") === "high" ? "high" : "normal",
      tasks,
    };
    setValidationError("");
    requestWriter((writer) => save(payload, writer));
  }

  return (
    <AppShell activeSection="new-request">
      <div className="page-header">
        <p>NEW VOC REQUEST</p>
        <h1>신규 고객 요청</h1>
        <span>메일 확인, 요청 정보 확정, 부서 과제 배정 순서로 서버 초안을 저장합니다.</span>
      </div>
      <WriterGate>
        {(requestWriter) => (
          <form ref={formRef} noValidate aria-busy={saving} onSubmit={(event) => submit(event, requestWriter)}>
            <section className="filter-panel" aria-labelledby="mail-step-heading">
              <h2 id="mail-step-heading">1. 메일 붙여넣기</h2>
              <label className="search-field"><span>원본 메일</span><textarea name="original_mail_body" rows={8} /></label>
              <button className="secondary-button" type="button" onClick={analyzeMail}>메일 내용 확인</button>
            </section>
            {confirmed && (
              <>
                <section className="filter-panel" aria-labelledby="confirm-step-heading">
                  <h2 id="confirm-step-heading">2. 추출 정보 확인</h2>
                  <div className="filter-grid">
                    <label><span>발신자명</span><input name="sender_name" defaultValue={parsed.sender_name} /></label>
                    <label><span>발신자 이메일</span><input name="sender_email" type="email" defaultValue={parsed.sender_email} /></label>
                    <label><span>발신 회사</span><input name="sender_company" defaultValue={parsed.sender_company} /></label>
                    <label><span>VOC Type</span><select name="voc_type" defaultValue=""><option value="">선택</option><option value="Inquiry">Inquiry</option><option value="Complaint">Complaint</option><option value="Request">Request</option></select></label>
                    <label><span>VOC Subtype</span><input name="voc_subtype" /></label>
                    <label><span>제품 / 설비</span><input name="product_equipment" /></label>
                    <label><span>우선순위</span><select name="priority" defaultValue="normal"><option value="normal">일반</option><option value="high">높음</option></select></label>
                  </div>
                  <label className="search-field"><span>고객 요청</span><textarea name="customer_request" rows={4} /></label>
                </section>
                <section className="filter-panel" aria-labelledby="task-step-heading">
                  <h2 id="task-step-heading">3. 부서 과제 배정</h2>
                  {Array.from({ length: taskCount }, (_, index) => (
                    <fieldset className="task-editor" key={index}>
                      <legend>부서 과제 {index + 1}</legend>
                      <div className="filter-grid">
                        <label><span>담당 부서 {index + 1}</span><input name={`task_department_${index}`} /></label>
                        <label><span>담당자 {index + 1}</span><input name={`task_assignee_${index}`} /></label>
                        <label><span>담당자 이메일 {index + 1}</span><input name={`task_assignee_email_${index}`} type="email" /></label>
                        <label><span>직책자 {index + 1}</span><input name={`task_manager_${index}`} /></label>
                        <label><span>직책자 이메일 {index + 1}</span><input name={`task_manager_email_${index}`} type="email" /></label>
                        <label><span>완료 예정일 {index + 1}</span><input name={`task_due_${index}`} type="date" /></label>
                        <label><span>ECM 링크 {index + 1}</span><input name={`task_ecm_${index}`} type="url" /></label>
                      </div>
                    </fieldset>
                  ))}
                  <div className="button-row">
                    <button className="secondary-button" type="button" onClick={() => setTaskCount((count) => count + 1)}>부서 과제 추가</button>
                    <button className="primary-button" type="submit" disabled={saving}>{saving ? "저장 중..." : "임시 저장"}</button>
                  </div>
                </section>
              </>
            )}
            {validationError && <p className="state-panel" role="alert">{validationError}</p>}
            {saveError && <p className="state-panel" role="alert">저장하지 못했습니다. 입력 내용을 확인하고 다시 시도해 주세요.</p>}
          </form>
        )}
      </WriterGate>
      {savedCaseId && (
        <section aria-labelledby="draft-result-heading">
          <div className="results-heading filter-panel">
            <div><h2 id="draft-result-heading">임시 저장됨: {savedCaseId}</h2><p>전체 단계는 요청 접수로 시작합니다.</p></div>
            <a className="primary-link" href={`/voc/${encodeURIComponent(savedCaseId)}`} aria-label={`${savedCaseId} 관리 화면`}>관리 화면</a>
          </div>
          <div className="page-header"><p>TOP 3</p><h2>유사한 종료 사례</h2></div>
          {similarError ? (
            <div className="state-panel" role="alert"><p>유사 사례를 불러오지 못했습니다.</p><button className="secondary-button" type="button" onClick={() => void loadSimilar(searchText)}>다시 시도</button></div>
          ) : similar.map((item) => (
            <article className="filter-panel" data-testid="similar-case" key={item.case_id}>
              <div className="results-heading"><div><h3>{item.case_id}</h3><p>{item.customer_name ?? "—"}</p></div><span>{item.final_status}</span></div>
              <p>{item.customer_request}</p>
              <a className="primary-link" href={`/archive/${encodeURIComponent(item.case_id)}`}>아카이브 상세</a>
            </article>
          ))}
        </section>
      )}
    </AppShell>
  );
}
