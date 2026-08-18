"use client";

import { useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import AppShell from "@/components/AppShell";
import WriterGate from "@/components/WriterGate";
import { createMasterData, getMasterData } from "@/lib/api";
import type { MasterRecord, MasterResource, WriterCredentials } from "@/lib/types";

const resources: MasterResource[] = [
  "customers",
  "products",
  "voc_types",
  "people",
  "final_approver",
  "templates",
  "notification_settings",
];

const emptyData = (): Record<MasterResource, MasterRecord[]> => ({
  customers: [],
  products: [],
  voc_types: [],
  people: [],
  final_approver: [],
  templates: [],
  notification_settings: [],
});

function text(form: FormData, name: string) {
  return String(form.get(name) ?? "").trim();
}

export default function AdminPage() {
  const [data, setData] = useState(emptyData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saveStatus, setSaveStatus] = useState<"" | "saving" | "saved">("");
  const saving = useRef(false);

  async function load(credentials: WriterCredentials) {
    const entries = await Promise.all(resources.map(async (resource) => [resource, await getMasterData(resource, credentials)] as const));
    setData(Object.fromEntries(entries) as Record<MasterResource, MasterRecord[]>);
  }

  async function open(credentials: WriterCredentials) {
    setLoading(true);
    setError("");
    try {
      await load(credentials);
    } catch {
      setError("관리 기준정보를 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function save(
    event: FormEvent<HTMLFormElement>,
    resource: MasterResource,
    payload: (form: FormData) => Record<string, unknown>,
    writer: WriterCredentials,
  ) {
    event.preventDefault();
    if (saving.current) return;
    saving.current = true;
    const form = event.currentTarget;
    setError("");
    setSaveStatus("saving");
    try {
      await createMasterData(resource, payload(new FormData(form)), writer);
      form.reset();
      await load(writer);
      setSaveStatus("saved");
    } catch {
      setSaveStatus("");
      setError("기준정보를 저장하지 못했습니다. 입력값을 확인해 주세요.");
    } finally {
      saving.current = false;
    }
  }

  const approvers = data.people.filter((person) => person.role === "final_approver");
  const finalApproverId = String(data.final_approver[0]?.person_id ?? "");
  const notificationTime = String(data.notification_settings[0]?.weekday_time ?? "09:00").slice(0, 5);

  return (
    <AppShell activeSection="admin">
      <div className="page-header"><p>MANAGEMENT TOOL</p><h1>관리 도구</h1><span>기준정보, 최종 승인자, 알림 시각과 템플릿을 관리합니다.</span></div>
      <WriterGate>
        {(requestWriter, writer) => !writer ? (
          <section className="state-panel"><p>관리 작업은 작성자 확인이 필요합니다.</p><button className="primary-button" type="button" onClick={() => requestWriter(open)}>관리 시작</button></section>
        ) : loading ? <p className="state-panel" role="status">관리 기준정보를 불러오는 중입니다.</p> : (
          <>
            <div className="admin-grid">
              <AdminSection title="고객사" count={data.customers.length}>
                <form onSubmit={(event) => void save(event, "customers", (form) => ({ name: text(form, "name"), active: true }), writer)}>
                  <label><span>고객사명</span><input name="name" required /></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>고객사 추가</button>
                </form>
              </AdminSection>

              <AdminSection title="제품 / 설비" count={data.products.length}>
                <form onSubmit={(event) => void save(event, "products", (form) => ({ name: text(form, "name"), active: true }), writer)}>
                  <label><span>제품 / 설비명</span><input name="name" required /></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>제품 / 설비 추가</button>
                </form>
              </AdminSection>

              <AdminSection title="VOC 유형 / 세부 유형" count={data.voc_types.length}>
                <form onSubmit={(event) => void save(event, "voc_types", (form) => ({ voc_type: text(form, "voc_type"), voc_subtype: text(form, "voc_subtype"), active: true }), writer)}>
                  <label><span>VOC 유형</span><input name="voc_type" required /></label>
                  <label><span>VOC 세부 유형</span><input name="voc_subtype" required /></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>VOC 유형 추가</button>
                </form>
              </AdminSection>

              <AdminSection title="담당자 / 직책자" count={data.people.length}>
                <form onSubmit={(event) => void save(event, "people", (form) => ({ department: text(form, "department"), name: text(form, "name"), email: text(form, "email"), role: text(form, "role"), active: true }), writer)}>
                  <label><span>담당 부서</span><input name="department" required /></label>
                  <label><span>담당자명</span><input name="name" required /></label>
                  <label><span>담당자 이메일</span><input name="email" type="email" required /></label>
                  <label><span>역할</span><select name="role"><option value="task_owner">과제 담당자</option><option value="department_manager">부서 직책자</option><option value="final_approver">최종 승인자</option></select></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>담당자 추가</button>
                </form>
              </AdminSection>

              <AdminSection title="고정 최종 승인자" count={data.final_approver.length}>
                <form key={finalApproverId} onSubmit={(event) => void save(event, "final_approver", (form) => ({ person_id: Number(text(form, "person_id")) }), writer)}>
                  <label><span>고정 최종 승인자</span><select name="person_id" defaultValue={finalApproverId} required><option value="">선택</option>{approvers.map((person) => <option key={String(person.id)} value={String(person.id)}>{String(person.department)} · {String(person.name)}</option>)}</select></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>최종 승인자 저장</button>
                </form>
              </AdminSection>

              <AdminSection title="알림 템플릿" count={data.templates.length}>
                <form onSubmit={(event) => void save(event, "templates", (form) => ({ template_key: text(form, "template_key"), subject_template: text(form, "subject_template"), body_template: text(form, "body_template"), active: true }), writer)}>
                  <label><span>템플릿 키</span><input name="template_key" required /></label>
                  <label><span>제목 템플릿</span><input name="subject_template" required /></label>
                  <label><span>본문 템플릿</span><textarea name="body_template" rows={4} required /></label>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>템플릿 저장</button>
                </form>
              </AdminSection>

              <AdminSection title="알림 시각" count={data.notification_settings.length}>
                <form key={notificationTime} onSubmit={(event) => void save(event, "notification_settings", (form) => ({ weekday_time: text(form, "weekday_time"), timezone_name: "Asia/Seoul" }), writer)}>
                  <label><span>평일 알림 시각</span><input name="weekday_time" type="time" defaultValue={notificationTime} required /></label>
                  <p>시간대: Asia/Seoul</p>
                  <button className="primary-button" type="submit" disabled={saveStatus === "saving"}>알림 시각 저장</button>
                </form>
              </AdminSection>
            </div>
            {saveStatus && <p className="save-status" role="status" aria-live="polite">{saveStatus === "saving" ? "저장 중입니다." : "저장했습니다."}</p>}
            {error && <p className="state-panel" role="alert">{error}</p>}
          </>
        )}
      </WriterGate>
    </AppShell>
  );
}

function AdminSection({ title, count, children }: { title: string; count: number; children: ReactNode }) {
  return <section className="admin-panel"><header><h2>{title}</h2><span>{count}건 등록</span></header>{children}</section>;
}
