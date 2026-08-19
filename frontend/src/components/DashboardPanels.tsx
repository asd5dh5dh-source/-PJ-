"use client";

import { useEffect, useState } from "react";

import { getDashboard } from "@/lib/api";
import type { DashboardData, DashboardPeriod } from "@/lib/types";

const stageLabels: Record<string, string> = {
  received: "접수",
  managing: "관리 중",
  in_progress: "대응 중",
  department_work: "부서별 검토 요청",
  department_review: "직책자 검토 요청",
  manager_review: "직책자 검토 요청",
  final_review: "최종 승인",
  customer_reply: "고객 회신",
  completed: "완료",
};

const taskLabels: Record<string, string> = {
  not_started: "시작 전",
  reviewing: "검토 중",
  in_progress: "조치 중",
  completed: "완료",
  delayed: "지연",
  excluded: "제외",
};

export default function DashboardPanels() {
  const [data, setData] = useState<DashboardData>();
  const [request, setRequest] = useState<{ period?: DashboardPeriod; date_from?: string; date_to?: string }>({ period: "30d" });
  const [preset, setPreset] = useState<DashboardPeriod | "custom">("30d");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    setError(false);
    getDashboard(request, controller.signal)
      .then(setData)
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(true);
      });
    return () => controller.abort();
  }, [request]);

  function choosePeriod(value: DashboardPeriod | "custom") {
    setPreset(value);
    if (value !== "custom") setRequest({ period: value });
  }

  return (
    <>
      <section className="filter-panel dashboard-filter" aria-label="대시보드 조회 기간">
        <label><span>조회 기간</span><select value={preset} onChange={(event) => choosePeriod(event.target.value as DashboardPeriod | "custom")}>
          <option value="30d">최근 30일</option>
          <option value="week">이번 주</option>
          <option value="month">이번 달</option>
          <option value="custom">사용자 지정</option>
        </select></label>
        {preset === "custom" && <>
          <label><span>시작일</span><input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
          <label><span>종료일</span><input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
          <button className="primary-button" type="button" disabled={!dateFrom || !dateTo} onClick={() => setRequest({ date_from: dateFrom, date_to: dateTo })}>기간 적용</button>
        </>}
      </section>
      {error ? <p className="state-panel" role="alert">대시보드를 불러오지 못했습니다.</p> : !data ? <p className="state-panel" role="status">대시보드를 불러오는 중입니다.</p> : (
        <div className="dashboard-grid">
          <section className="dashboard-panel" aria-labelledby="stage-panel-heading">
            <h2 id="stage-panel-heading">단계별 VOC 현황</h2>
            {data.stage_counts.length ? <ul>{data.stage_counts.map((item) => <li key={item.stage}><span>{stageLabels[item.stage] ?? item.stage}</span><strong>{item.count}건</strong></li>)}</ul> : <p>해당 기간의 VOC가 없습니다.</p>}
          </section>
          <section className="dashboard-panel" aria-labelledby="due-panel-heading">
            <h2 id="due-panel-heading">마감 임박/지연 부서 과제</h2>
            {data.due_tasks.length ? <ul>{data.due_tasks.map((task) => <li key={task.id}><a href={task.case_id ? `/voc/${task.case_id}` : undefined}>{task.case_id ?? `과제 #${task.id}`}</a><span>{task.department ?? "담당 부서 미정"} · {taskLabels[task.status] ?? task.status}</span>{task.due_date && <small>기한 {task.due_date}</small>}</li>)}</ul> : <p>마감 임박 또는 지연 과제가 없습니다.</p>}
          </section>
          <section className="dashboard-panel" aria-labelledby="active-panel-heading">
            <h2 id="active-panel-heading">현재 진행 VOC</h2>
            {data.active_requests.length ? <ul>{data.active_requests.map((request) => <li key={request.case_id}><a href={`/voc/${request.case_id}`}>{request.case_id}</a><span>{request.sender_company ?? "고객사 미정"}</span>{request.voc_type && request.voc_subtype && <small>{request.voc_type} · {request.voc_subtype}</small>}{request.responsible_departments && <small>담당 {request.responsible_departments}</small>}{request.stage && <small>{stageLabels[request.stage] ?? request.stage}</small>}</li>)}</ul> : <p>진행 중인 VOC가 없습니다.</p>}
          </section>
        </div>
      )}
    </>
  );
}
