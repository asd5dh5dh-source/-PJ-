import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "./page";

const dashboard = {
  stage_counts: [{ stage: "received", count: 2 }],
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
    expect(screen.getByRole("heading", { name: "마감 임박/지연 부서 과제" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "최근 고객 요청" })).toBeVisible();
    expect(screen.getByText("Example Materials")).toBeVisible();
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
