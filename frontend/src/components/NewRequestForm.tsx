"use client";

import { useRef, useState } from "react";

import { createManualRequest } from "@/lib/api";
import type { ManualRequestInput } from "@/lib/api";

export default function NewRequestForm({ onSaved }: { onSaved: (caseId: string) => void }) {
  const inFlight = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(false);

  async function submit(form: HTMLFormElement) {
    if (inFlight.current) return;
    inFlight.current = true;
    setSubmitting(true);
    setError(false);

    const values = new FormData(form);
    const value = (name: string) => String(values.get(name) ?? "").trim();
    const optional = (name: string) => value(name) || undefined;
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
        onSubmit={(event) => {
          event.preventDefault();
          void submit(event.currentTarget);
        }}
      >
        <label className="search-field">
          <span>원본 메일</span>
          <textarea name="original_mail_body" rows={8} required />
        </label>
        <div className="filter-grid">
          <label><span>고객명</span><input name="customer_name" required /></label>
          <label>
            <span>VOC Type</span>
            <select name="voc_type" defaultValue="" required>
              <option value="" disabled>선택</option>
              <option value="Inquiry">Inquiry</option>
              <option value="Complaint">Complaint</option>
              <option value="Request">Request</option>
            </select>
          </label>
          <label><span>VOC Subtype</span><input name="voc_subtype" required /></label>
          <label><span>제품 / 설비</span><input name="product_equipment" /></label>
          <label><span>담당 부서</span><input name="responsible_departments" /></label>
        </div>
        <label className="search-field">
          <span>고객 요청</span>
          <textarea name="customer_request" rows={4} required />
        </label>
        {error && <p role="alert">요청을 저장하지 못했습니다. 입력 내용을 확인하고 다시 시도해 주세요.</p>}
        <button className="primary-button" type="submit" disabled={submitting}>
          {submitting ? "저장 중..." : "저장 및 유사 사례 검색"}
        </button>
      </form>
    </section>
  );
}
