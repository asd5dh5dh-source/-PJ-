import type { ReactNode } from "react";

export default function AppShell({
  children,
  activeSection = "archive",
}: {
  children: ReactNode;
  activeSection?: "dashboard" | "archive" | "new-request" | "voc" | "notifications" | "admin";
}) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
      <div className="sidebar">
        <a className="brand" href="/" aria-label="VOC Hub 홈">
          <span aria-hidden="true">VH</span>
          <strong>VOC Hub</strong>
        </a>
        <nav aria-label="업무 메뉴">
          <a href="/" aria-current={activeSection === "dashboard" ? "page" : undefined}>대시보드</a>
          <a href="/archive" aria-current={activeSection === "archive" ? "page" : undefined}>VOC 아카이브</a>
          <a href="/requests/new" aria-current={activeSection === "new-request" ? "page" : undefined}>신규 요청</a>
          <a href="/notifications" aria-current={activeSection === "notifications" ? "page" : undefined}>알림</a>
          <a href="/admin" aria-current={activeSection === "admin" ? "page" : undefined}>관리 도구</a>
        </nav>
        <p className="sidebar-note">사내 VOC 검색</p>
      </div>
      <div className="app-content">
        <header className="topbar">
          <span>Customer Quality Intelligence</span>
          <span className="internal-label">INTERNAL</span>
        </header>
        <main id="main-content">{children}</main>
      </div>
    </div>
  );
}
