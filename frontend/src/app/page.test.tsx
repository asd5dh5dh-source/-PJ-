import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "./page";

const dashboard = {
  stage_counts: [{ stage: "received", count: 2 }],
  monthly_voc_counts: [
    { month: "2026-07", complaint: 3, request: 2, inquiry: 1 },
    { month: "2026-08", complaint: 2, request: 1, inquiry: 0 },
  ],
  due_tasks: [{
    id: 4,
    case_id: "VOC-2026-0002",
    department: "품질",
    status: "delayed",
    due_date: "2026-08-17",
    sender_email: "private@example.com",
  }],
  recent_requests: [{
    case_id: "VOC-2026-0003",
    sender_company: "Example Materials",
    product_equipment: "NCA",
    stage: "in_progress",
    original_mail_body: "private mail",
  }],
  active_requests: [{
    case_id: "VOC-2026-0004",
    sender_company: "Example Materials",
    voc_type: "Complaint",
    voc_subtype: "Gas Generation",
    stage: "in_progress",
  }],
};

describe("DashboardPage", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify(dashboard), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
  });

  it("shows the three equal-weight public dashboard panels without sensitive fields", async () => {
    render(<DashboardPage />);

    expect(await screen.findByRole("heading", { name: "단계별 VOC 현황" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "월별 접수 VOC" })).toBeVisible();
    expect(screen.getByLabelText("2026-07 Complaint 3건")).toBeVisible();
    expect(screen.getByLabelText("2026-08 Inquiry 0건")).toBeVisible();
    expect(screen.getByRole("heading", { name: "마감 임박/지연 부서 과제" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "현재 진행 VOC" })).toBeVisible();
    expect(screen.getByText("Example Materials")).toBeVisible();
    expect(screen.getByText("Complaint · Gas Generation")).toBeVisible();
    expect(screen.queryByText("private@example.com")).not.toBeInTheDocument();
    expect(screen.queryByText("private mail")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/dashboard?period=30d", expect.any(Object));
  });

  it("reloads the dashboard for the selected date preset", async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);
    await screen.findByText("Example Materials");

    await user.selectOptions(screen.getByRole("combobox", { name: "조회 기간" }), "week");

    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/dashboard?period=week",
      expect.any(Object),
    ));
  });

  it("loads a user-selected custom date range", async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);
    await screen.findByText("Example Materials");

    await user.selectOptions(screen.getByRole("combobox", { name: "조회 기간" }), "custom");
    await user.type(screen.getByLabelText("시작일"), "2026-08-01");
    await user.type(screen.getByLabelText("종료일"), "2026-08-10");
    await user.click(screen.getByRole("button", { name: "기간 적용" }));

    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith(
      "/api/dashboard?date_from=2026-08-01&date_to=2026-08-10",
      expect.any(Object),
    ));
  });
});
