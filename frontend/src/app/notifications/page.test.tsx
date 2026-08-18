import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotificationsPage from "./page";

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify([{
        id: 1,
        recipients: ["owner@example.com"],
        subject: "VOC-2026-0001 기한 알림",
        body: "품질 과제의 기한이 임박했습니다.",
        scheduled_at: "2026-08-19T00:00:00Z",
        sent_at: null,
        runtime_profile: "external_review",
        delivery_status: "preview",
        real_delivery: false,
        created_at: "2026-08-18T00:00:00Z",
      }]),
      { status: 200, headers: { "Content-Type": "application/json" } },
    )));
  });

  it("shows notification logs and an on-demand template preview without recipient addresses", async () => {
    const user = userEvent.setup();
    render(<NotificationsPage />);

    expect(await screen.findByRole("heading", { name: "예정 및 미리보기" })).toBeVisible();
    expect(screen.getByText("VOC-2026-0001 기한 알림")).toBeVisible();
    expect(screen.queryByText("owner@example.com")).not.toBeInTheDocument();

    await user.click(screen.getByText("템플릿 미리보기"));
    expect(screen.getByText("품질 과제의 기한이 임박했습니다.")).toBeVisible();
  });
});
