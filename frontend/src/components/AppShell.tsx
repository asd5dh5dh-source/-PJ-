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
      <div className="sidebar sidebar-light">
        <a className="brand" href="/" aria-label="고객 요청 대응 플랫폼 홈">
          <span aria-hidden="true">V</span>
          <strong>고객 요청 대응 플랫폼</strong>
        </a>
        <nav aria-label="업무 메뉴">
          <a className="nav-link" href="/" aria-current={activeSection === "dashboard" ? "page" : undefined}>대시보드</a>
          <a className="nav-link" href="/archive" aria-current={activeSection === "archive" ? "page" : undefined}>VOC 아카이브</a>
          <a className="nav-link" href="/requests/new" aria-current={activeSection === "new-request" ? "page" : undefined}>신규 요청</a>
          <a className="nav-link" href="/notifications" aria-current={activeSection === "notifications" ? "page" : undefined}>알림</a>
          <a className="nav-link" href="/admin" aria-current={activeSection === "admin" ? "page" : undefined}>관리 도구</a>
        </nav>
        <p className="sidebar-note">VOC 지식 아카이브</p>
      </div>
      <div className="app-content">
        <header className="topbar">
          <span>운영 업무 공간</span>
          <span className="internal-label">내부 운영</span>
        </header>
        <main id="main-content">{children}</main>
      </div>
    </div>
  );
}
