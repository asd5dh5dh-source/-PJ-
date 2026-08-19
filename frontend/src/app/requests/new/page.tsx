"use client";

import { useRef, useState } from "react";
import type { FormEvent } from "react";

import AppShell from "@/components/AppShell";
import WriterGate from "@/components/WriterGate";
import type { RequestWriter } from "@/components/WriterGate";
import { analyzeMail, createVoc, getArchive } from "@/lib/api";
import type { ArchiveItem, VocCreateInput, WriterCredentials } from "@/lib/types";

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
  const [suggestions, setSuggestions] = useState({ voc_type: "", voc_subtype: "", product_equipment: "" });
  const [translationDraft, setTranslationDraft] = useState("");
  const [keywords, setKeywords] = useState<string[]>([]);
  const [customerRequestDraft, setCustomerRequestDraft] = useState("");
  const [priority, setPriority] = useState<"normal" | "high">("normal");
  const [taskCount, setTaskCount] = useState(1);
  const [taskDepartments, setTaskDepartments] = useState<string[]>([""]);
  const [saving, setSaving] = useState(false);
  const [validationError, setValidationError] = useState("");
  const [saveError, setSaveError] = useState(false);
  const [similarError, setSimilarError] = useState(false);
  const [savedCaseId, setSavedCaseId] = useState("");
  const [similar, setSimilar] = useState<ArchiveItem[]>([]);
  const [searchContext, setSearchContext] = useState({ query: "", subtype: "" });

  async function analyzePastedMail() {
    const mail = formRef.current?.elements.namedItem("original_mail_body");
    if (!(mail instanceof HTMLTextAreaElement) || !mail.value.trim()) {
      setValidationError("원본 메일을 입력해 주세요.");
      return;
    }
    setSimilarError(false);
    try {
      const analysis = await analyzeMail(mail.value);
      setParsed({
        sender_name: analysis.sender_name ?? "",
        sender_email: analysis.sender_email ?? "",
        sender_company: analysis.sender_company ?? "",
      });
      setSuggestions({
        voc_type: analysis.suggested_voc_type ?? "",
        voc_subtype: analysis.suggested_voc_subtype ?? "",
        product_equipment: analysis.suggested_product_equipment ?? "",
      });
      setTranslationDraft(analysis.translation_draft ?? "");
      setKeywords(analysis.extracted_keywords ?? []);
      setCustomerRequestDraft(analysis.suggested_customer_request ?? "");
      setPriority(analysis.suggested_priority);
      setTaskDepartments(analysis.suggested_departments.length ? analysis.suggested_departments : [""]);
      setTaskCount(Math.max(1, analysis.suggested_departments.length));
      setSimilar(analysis.items);
      setValidationError("");
      setConfirmed(true);
    } catch {
      setValidationError("메일 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    }
  }

  async function loadSimilar(query: string, subtype: string) {
    setSimilarError(false);
    try {
      const page = await getArchive({
        q: query,
        boost_voc_subtype: subtype,
        final_status: "closed",
        sort: "relevance",
      });
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
      const context = {
        query: [payload.customer_request, payload.original_mail_body].filter(Boolean).join("\n\n"),
        subtype: payload.voc_subtype ?? "",
      };
      setSearchContext(context);
      await loadSimilar(context.query, context.subtype);
    } catch {
      setSaveError(true);
    } finally {
      setSaving(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>, requestWriter: RequestWriter) {
    event.preventDefault();
    if (saving || savedCaseId) return;
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
      translation_draft: optional(field(values, "translation_draft")),
      voc_type: vocType,
      voc_subtype: vocSubtype,
      product_equipment: optional(field(values, "product_equipment")),
      priority,
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
              <button className="secondary-button" type="button" onClick={() => void analyzePastedMail()}>메일 내용 확인</button>
            </section>
            {confirmed && (
              <>
                <section className="filter-panel" aria-labelledby="confirm-step-heading">
                  <h2 id="confirm-step-heading">2. 추출 정보 확인</h2>
                  <div className="filter-grid">
                    <label><span>발신자명</span><input name="sender_name" value={parsed.sender_name} onChange={(event) => setParsed((value) => ({ ...value, sender_name: event.target.value }))} /></label>
                    <label><span>발신자 이메일</span><input name="sender_email" type="email" value={parsed.sender_email} onChange={(event) => setParsed((value) => ({ ...value, sender_email: event.target.value }))} /></label>
                    <label><span>발신 회사</span><input name="sender_company" value={parsed.sender_company} onChange={(event) => setParsed((value) => ({ ...value, sender_company: event.target.value }))} /></label>
                    <label><span>VOC Type</span><select name="voc_type" value={suggestions.voc_type} onChange={(event) => setSuggestions((value) => ({ ...value, voc_type: event.target.value }))}><option value="">선택</option><option value="Inquiry">Inquiry</option><option value="Complaint">Complaint</option><option value="Request">Request</option></select></label>
                    <label><span>VOC Subtype</span><input name="voc_subtype" value={suggestions.voc_subtype} onChange={(event) => setSuggestions((value) => ({ ...value, voc_subtype: event.target.value }))} /></label>
                    <label><span>제품 / 설비</span><input name="product_equipment" value={suggestions.product_equipment} onChange={(event) => setSuggestions((value) => ({ ...value, product_equipment: event.target.value }))} /></label>
                    <label><span>우선순위</span><select name="priority" value={priority} onChange={(event) => setPriority(event.target.value === "high" ? "high" : "normal")}><option value="normal">일반</option><option value="high">높음</option></select></label>
                  </div>
                  {keywords.length > 0 && <p className="state-panel">문제 키워드: {keywords.join(", ")}</p>}
                  {translationDraft && <label className="search-field"><span>한국어 번역 초안</span><textarea name="translation_draft" rows={4} value={translationDraft} onChange={(event) => setTranslationDraft(event.target.value)} /></label>}
                  <label className="search-field"><span>고객 요청</span><textarea name="customer_request" rows={4} value={customerRequestDraft} onChange={(event) => setCustomerRequestDraft(event.target.value)} /></label>
                </section>
                <section className="filter-panel" aria-labelledby="task-step-heading">
                  <h2 id="task-step-heading">3. 부서 과제 배정</h2>
                  {Array.from({ length: taskCount }, (_, index) => (
                    <fieldset className="task-editor" key={index}>
                      <legend>부서 과제 {index + 1}</legend>
                      <div className="filter-grid">
                        <label><span>담당 부서 {index + 1}</span><input name={`task_department_${index}`} value={taskDepartments[index] ?? ""} onChange={(event) => setTaskDepartments((items) => items.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>
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
                    <button className="secondary-button" type="button" onClick={() => { setTaskCount((count) => count + 1); setTaskDepartments((items) => [...items, ""]); }}>부서 과제 추가</button>
                    <button className="primary-button" type="submit" disabled={saving || Boolean(savedCaseId)}>{savedCaseId ? "저장 완료" : saving ? "저장 중..." : "임시 저장"}</button>
                  </div>
                </section>
              </>
            )}
            {validationError && <p className="state-panel" role="alert">{validationError}</p>}
            {saveError && <p className="state-panel" role="alert">저장하지 못했습니다. 입력 내용을 확인하고 다시 시도해 주세요.</p>}
          </form>
        )}
      </WriterGate>
      {confirmed && (
        <section aria-labelledby="similar-result-heading">
          <div className="page-header"><p>TOP 3</p><h2 id="similar-result-heading">유사한 종료 사례</h2></div>
          {similarError ? (
            <div className="state-panel" role="alert"><p>유사 사례를 불러오지 못했습니다.</p><button className="secondary-button" type="button" onClick={() => void loadSimilar(searchContext.query, searchContext.subtype)}>다시 시도</button></div>
          ) : similar.map((item) => (
            <article className="filter-panel" data-testid="similar-case" key={item.case_id}>
              <div className="results-heading"><div><h3>{item.case_id}</h3><p>{item.customer_name ?? "—"}</p></div><span>{item.final_status}</span></div>
              <p>{item.customer_request}</p>
              <a className="primary-link" href={`/archive/${encodeURIComponent(item.case_id)}`}>아카이브 상세</a>
            </article>
          ))}
        </section>
      )}
      {savedCaseId && <section className="results-heading filter-panel"><div><h2>임시 저장됨: {savedCaseId}</h2><p>전체 단계는 요청 접수로 시작합니다.</p></div><a className="primary-link" href={`/voc/${encodeURIComponent(savedCaseId)}`} aria-label={`${savedCaseId} 관리 화면`}>관리 화면</a></section>}
    </AppShell>
  );
}
