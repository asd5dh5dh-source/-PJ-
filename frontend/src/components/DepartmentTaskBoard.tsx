"use client";

import { useEffect, useState } from "react";
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

type TaskForm = {
  status: TaskStatus;
  response_content: string;
  due_date: string;
  delay_reason: string;
  ecm_link: string;
};

function taskForm(task: DepartmentTask): TaskForm {
  return {
    status: task.status,
    response_content: task.response_content ?? "",
    due_date: task.due_date ?? "",
    delay_reason: task.delay_reason ?? "",
    ecm_link: task.ecm_link ?? "",
  };
}

function TaskEditor({
  task,
  onSubmit,
}: {
  task: DepartmentTask;
  onSubmit: (event: FormEvent<HTMLFormElement>, task: DepartmentTask, values: TaskForm) => void;
}) {
  const [values, setValues] = useState(() => taskForm(task));
  useEffect(() => setValues(taskForm(task)), [task]);
  const change = (field: keyof TaskForm, value: string) => {
    setValues((current) => ({ ...current, [field]: value } as TaskForm));
  };

  return (
    <form onSubmit={(event) => onSubmit(event, task, values)}>
      <label><span>과제 상태</span><select name="status" value={values.status} onChange={(event) => change("status", event.target.value)}>{Object.entries(taskStatusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
      <label><span>대응 내용</span><textarea name="response_content" rows={3} value={values.response_content} onChange={(event) => change("response_content", event.target.value)} /></label>
      <div className="filter-grid">
        <label><span>완료 예정일</span><input name="due_date" type="date" value={values.due_date} onChange={(event) => change("due_date", event.target.value)} /></label>
        <label><span>지연 사유</span><input name="delay_reason" value={values.delay_reason} onChange={(event) => change("delay_reason", event.target.value)} /></label>
        <label><span>ECM 링크</span><input name="ecm_link" type="url" value={values.ecm_link} onChange={(event) => change("ecm_link", event.target.value)} /></label>
      </div>
      <div className="button-row">
        {task.ecm_link && <a className="primary-link" href={task.ecm_link} target="_blank" rel="noreferrer" aria-label={`${task.department} ECM 문서`}>ECM 문서</a>}
        <button className="secondary-button" type="submit">과제 저장</button>
      </div>
    </form>
  );
}

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

  function submit(event: FormEvent<HTMLFormElement>, task: DepartmentTask, values: TaskForm) {
    event.preventDefault();
    requestWriter(async (writer) => {
      setError("");
      try {
        await updateDepartmentTask(task.id, {
          status: values.status,
          response_content: values.response_content.trim() || undefined,
          due_date: values.due_date || undefined,
          delay_reason: values.delay_reason.trim() || undefined,
          ecm_link: values.ecm_link.trim() || undefined,
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
            <TaskEditor task={task} onSubmit={submit} />
          </article>
        ))}
      </div>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
