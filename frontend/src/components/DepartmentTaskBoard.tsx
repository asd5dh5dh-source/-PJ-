"use client";

import { useState } from "react";
import type { FormEvent } from "react";

import type { RequestWriter } from "./WriterGate";
import { updateDepartmentTask } from "@/lib/api";
import type { DepartmentTask, TaskStatus } from "@/lib/types";

export const taskStatusLabels: Record<TaskStatus, string> = {
  not_started: "미착수",
  reviewing: "재검토",
  in_progress: "조치 중",
  completed: "완료",
  delayed: "지연",
  excluded: "제외",
};

export default function DepartmentTaskBoard({
  tasks,
  requestWriter,
  onChanged,
}: {
  tasks: DepartmentTask[];
  requestWriter: RequestWriter;
  onChanged: () => Promise<void>;
}) {
  const [error, setError] = useState("");

  function submit(event: FormEvent<HTMLFormElement>, task: DepartmentTask) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    requestWriter(async (writer) => {
      setError("");
      try {
        await updateDepartmentTask(task.id, {
          status: String(values.get("status")) as TaskStatus,
          response_content: String(values.get("response_content") ?? "").trim() || undefined,
          due_date: String(values.get("due_date") ?? "") || undefined,
          delay_reason: String(values.get("delay_reason") ?? "").trim() || undefined,
          ecm_link: String(values.get("ecm_link") ?? "").trim() || undefined,
        }, writer);
        await onChanged();
      } catch {
        setError("부서 과제를 저장하지 못했습니다.");
      }
    });
  }

  return (
    <section className="filter-panel" aria-labelledby="task-board-heading">
      <h2 id="task-board-heading">부서별 과제</h2>
      {tasks.length === 0 && <p>배정된 부서 과제가 없습니다.</p>}
      <div className="task-board">
        {tasks.map((task) => (
          <article key={task.id}>
            <header>
              <h3>{task.department} · {taskStatusLabels[task.status]}</h3>
              <span>{task.assignee_name || "담당자 미정"}</span>
            </header>
            <form onSubmit={(event) => submit(event, task)}>
              <label><span>과제 상태</span><select name="status" defaultValue={task.status}>{Object.entries(taskStatusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
              <label><span>대응 내용</span><textarea name="response_content" rows={3} defaultValue={task.response_content ?? ""} /></label>
              <div className="filter-grid">
                <label><span>완료 예정일</span><input name="due_date" type="date" defaultValue={task.due_date ?? ""} /></label>
                <label><span>지연 사유</span><input name="delay_reason" defaultValue={task.delay_reason ?? ""} /></label>
                <label><span>ECM 링크</span><input name="ecm_link" type="url" defaultValue={task.ecm_link ?? ""} /></label>
              </div>
              <div className="button-row">
                {task.ecm_link && <a className="primary-link" href={task.ecm_link} target="_blank" rel="noreferrer" aria-label={`${task.department} ECM 문서`}>ECM 문서</a>}
                <button className="secondary-button" type="submit">과제 저장</button>
              </div>
            </form>
          </article>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
