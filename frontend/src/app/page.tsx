import AppShell from "@/components/AppShell";
import DashboardPanels from "@/components/DashboardPanels";

export default function DashboardPage() {
  return (
    <AppShell activeSection="dashboard">
      <div className="page-header">
        <p>VOC DASHBOARD</p>
        <h1>VOC 운영 대시보드</h1>
        <span>공개 가능한 운영 현황만 요약해 보여줍니다.</span>
      </div>
      <DashboardPanels />
    </AppShell>
  );
}
