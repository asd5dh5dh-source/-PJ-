"use client";

import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { getNotifications } from "@/lib/api";
import type { NotificationLog } from "@/lib/types";

const statusLabels: Record<NotificationLog["delivery_status"], string> = {
  preview: "미리보기",
  pending: "발송 예정",
  sent: "발송 완료",
  failed: "발송 실패",
};

export default function NotificationsPage() {
  const [logs, setLogs] = useState<NotificationLog[]>();
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getNotifications(controller.signal).then(setLogs).catch((requestError: unknown) => {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(true);
    });
    return () => controller.abort();
  }, []);

  const pending = logs?.filter((log) => log.delivery_status === "preview" || log.delivery_status === "pending") ?? [];
  const history = logs?.filter((log) => log.delivery_status === "sent" || log.delivery_status === "failed") ?? [];

  return (
    <AppShell activeSection="notifications">
      <div className="page-header"><p>NOTIFICATIONS</p><h1>알림</h1><span>예정 알림과 발송 이력의 제목·본문 미리보기를 확인합니다.</span></div>
      {error ? <p className="state-panel" role="alert">알림 이력을 불러오지 못했습니다.</p> : !logs ? <p className="state-panel" role="status">알림 이력을 불러오는 중입니다.</p> : <div className="notification-grid">
        <NotificationSection heading="예정 및 미리보기" logs={pending} />
        <NotificationSection heading="발송 이력" logs={history} />
      </div>}
    </AppShell>
  );
}

function NotificationSection({ heading, logs }: { heading: string; logs: NotificationLog[] }) {
  return <section className="filter-panel notification-panel"><h2>{heading}</h2>{logs.length ? <div className="notification-list">{logs.map((log) => <article key={log.id}><header><strong>{log.subject}</strong><span className="status-badge">{statusLabels[log.delivery_status]}</span></header><small>{new Date(log.scheduled_at ?? log.sent_at ?? log.created_at).toLocaleString("ko-KR")}</small><details><summary>템플릿 미리보기</summary><p className="preserve-lines">{log.body}</p></details></article>)}</div> : <p>표시할 알림이 없습니다.</p>}</section>;
}
