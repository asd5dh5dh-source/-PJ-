"use client";

import { useState } from "react";

import type { RequestWriter } from "./WriterGate";
import { reviewDepartmentTask } from "@/lib/api";
import type { DepartmentTask, TaskReview } from "@/lib/types";

export default function ApprovalPanel({
  tasks,
  reviews,
  requestWriter,
  onChanged,
}: {
  tasks: DepartmentTask[];
  reviews: TaskReview[];
  requestWriter: RequestWriter;
  onChanged: () => Promise<void>;
}) {
  const [error, setError] = useState("");

  function review(
    task: DepartmentTask,
    reviewer_role: "department_manager" | "final_approver",
    decision: "approved" | "rejected",
  ) {
    requestWriter(async (writer) => {
      setError("");
      try {
        await reviewDepartmentTask(task.id, { reviewer_role, decision }, writer);
        await onChanged();
      } catch {
        setError("검토 결과를 저장하지 못했습니다.");
      }
    });
  }

  const activeTasks = tasks.filter((task) => task.status !== "excluded");
  return (
    <section className="filter-panel" aria-labelledby="approval-heading">
      <h2 id="approval-heading">승인과 반려</h2>
      {activeTasks.map((task) => {
        const latest = [...reviews].reverse().find((item) => item.task_id === task.id && item.reviewer_role === "department_manager");
        return (
          <div className="approval-row" key={task.id}>
            <span>{task.department} 직책자 {latest ? `${latest.decision} (${latest.reviewed_by ?? "—"})` : "검토 전"}</span>
            <div className="button-row">
              <button className="secondary-button" type="button" onClick={() => review(task, "department_manager", "rejected")} aria-label={`${task.department} 부서 반려`}>반려</button>
              <button className="primary-button" type="button" onClick={() => review(task, "department_manager", "approved")} aria-label={`${task.department} 부서 승인`}>승인</button>
            </div>
          </div>
        );
      })}
      {activeTasks[0] && (
        <div className="approval-row">
          <span>고정 최종 승인자</span>
          <div className="button-row">
            <button className="secondary-button" type="button" onClick={() => review(activeTasks[0], "final_approver", "rejected")}>최종 반려</button>
            <button className="primary-button" type="button" onClick={() => review(activeTasks[0], "final_approver", "approved")}>최종 승인</button>
          </div>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
