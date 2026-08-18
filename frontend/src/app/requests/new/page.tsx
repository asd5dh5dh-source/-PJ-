"use client";

import { useState } from "react";

import AppShell from "@/components/AppShell";
import NewRequestForm from "@/components/NewRequestForm";
import SimilarCases from "@/components/SimilarCases";

export default function NewRequestPage() {
  const [savedCaseId, setSavedCaseId] = useState<string>();

  return (
    <AppShell activeSection="new-request">
      <div className="page-header">
        <p>NEW VOC REQUEST</p>
        <h1>신규 고객 요청</h1>
        <span>메일 원문과 확인된 정보를 저장한 뒤 유사한 종료 사례를 확인합니다.</span>
      </div>
      <NewRequestForm onSaved={setSavedCaseId} />
      {savedCaseId && <SimilarCases caseId={savedCaseId} />}
    </AppShell>
  );
}
