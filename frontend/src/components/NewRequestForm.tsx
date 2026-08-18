"use client";

import { useRef, useState } from "react";

import { createManualRequest } from "@/lib/api";
import type { ManualRequestInput } from "@/lib/api";

const requiredFields = [
  ["original_mail_body", "원본 메일"],
  ["customer_name", "고객명"],
  ["voc_type", "VOC Type"],
  ["voc_subtype", "VOC Subtype"],
  ["customer_request", "고객 요청"],
] as const;

export default function NewRequestForm({ onSaved }: { onSaved: (caseId: string) => void }) {
  const inFlight = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);
  const [invalidField, setInvalidField] = useState<(typeof requiredFields)[number] | null>(null);

  async function submit(form: HTMLFormElement) {
    if (inFlight.current) return;

    const values = new FormData(form);
    const value = (name: string) => String(values.get(name) ?? "").trim();
    const optional = (name: string) => value(name) || undefined;
    const missing = requiredFields.find(([name]) => !value(name));
    if (missing) {
      setError(false);
      setInvalidField(missing);
      const field = form.elements.namedItem(missing[0]);
      if (field instanceof HTMLElement) field.focus();
      return;
    }

    setInvalidField(null);
    inFlight.current = true;
    setSubmitting(true);
    setError(false);
    const payload: ManualRequestInput = {
      customer_name: value("customer_name"),
      product_equipment: optional("product_equipment"),
      voc_type: value("voc_type"),
      voc_subtype: value("voc_subtype"),
      customer_request: value("customer_request"),
      original_mail_body: value("original_mail_body"),
      responsible_departments: optional("responsible_departments"),
    };

    try {
      const saved = await createManualRequest(payload);
      onSaved(saved.case_id);
    } catch {
      setError(true);
    } finally {
      inFlight.current = false;
      setSubmitting(false);
    }
  }

  return (
    <section className="filter-panel" aria-labelledby="new-request-heading">
      <h2 id="new-request-heading">메일 원문과 확인된 VOC 정보</h2>
      <form
        aria-busy={submitting}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void submit(event.currentTarget);
        }}
      >
        <label className="search-field">
          <span>원본 메일</span>
          <textarea
            name="original_mail_body"
            rows={8}
            required
            aria-invalid={invalidField?.[0] === "original_mail_body"}
            aria-describedby={invalidField?.[0] === "original_mail_body" ? "request-validation-error" : undefined}
          />
        </label>
        <div className="filter-grid">
          <label><span>고객명</span><input name="customer_name" required aria-invalid={invalidField?.[0] === "customer_name"} aria-describedby={invalidField?.[0] === "customer_name" ? "request-validation-error" : undefined} /></label>
          <label>
            <span>VOC Type</span>
            <select name="voc_type" defaultValue="" required aria-invalid={invalidField?.[0] === "voc_type"} aria-describedby={invalidField?.[0] === "voc_type" ? "request-validation-error" : undefined}>
              <option value="" disabled>선택</option>
              <option value="Inquiry">Inquiry</option>
              <option value="Complaint">Complaint</option>
              <option value="Request">Request</option>
            </select>
          </label>
          <label><span>VOC Subtype</span><input name="voc_subtype" required aria-invalid={invalidField?.[0] === "voc_subtype"} aria-describedby={invalidField?.[0] === "voc_subtype" ? "request-validation-error" : undefined} /></label>
          <label><span>제품 / 설비</span><input name="product_equipment" /></label>
          <label><span>담당 부서</span><input name="responsible_departments" /></label>
        </div>
        <label className="search-field">
          <span>고객 요청</span>
          <textarea name="customer_request" rows={4} required aria-invalid={invalidField?.[0] === "customer_request"} aria-describedby={invalidField?.[0] === "customer_request" ? "request-validation-error" : undefined} />
        </label>
        {invalidField && <p id="request-validation-error" role="alert">{invalidField[1]} 필드를 입력해 주세요.</p>}
        {error && <p role="alert">요청을 저장하지 못했습니다. 입력 내용을 확인하고 다시 시도해 주세요.</p>}
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "저장 중..." : "저장 및 유사 사례 검색"}
        </button>
      </form>
    </section>
  );
}
