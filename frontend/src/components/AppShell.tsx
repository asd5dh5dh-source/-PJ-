import type { ReactNode } from "react";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">본문으로 건너뛰기</a>
      <div className="sidebar">
        <a className="brand" href="/archive" aria-label="VOC Hub 홈">
          <span aria-hidden="true">VH</span>
          <strong>VOC Hub</strong>
        </a>
        <nav aria-label="업무 메뉴">
          <a href="/archive" aria-current="page">VOC 아카이브</a>
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
