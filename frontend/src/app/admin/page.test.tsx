import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AdminPage from "./page";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AdminPage", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/writer/verify")) return jsonResponse({ writer_name: "Kim" });
      if (url.endsWith("/people")) return jsonResponse([{ id: 8, department: "품질", name: "Park", email: "park@example.com", role: "final_approver" }]);
      if (url.endsWith("/final_approver")) return jsonResponse([{ singleton_id: 1, person_id: 8 }]);
      if (url.endsWith("/notification_settings")) return jsonResponse([{ singleton_id: 1, weekday_time: "08:30:00", timezone_name: "Asia/Seoul" }]);
      if (url.endsWith("/customers") && init?.method === "POST") return jsonResponse({ id: 2, name: "Acme", active: true }, 201);
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  it("requires writer verification before exposing every management form", async () => {
    const user = userEvent.setup();
    render(<AdminPage />);

    expect(screen.queryByLabelText("고객사명")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "관리 시작" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(await screen.findByLabelText("고객사명")).toBeVisible();
    expect(screen.getByLabelText("제품 / 설비명")).toBeVisible();
    expect(screen.getByLabelText("VOC 유형")).toBeVisible();
    expect(screen.getByLabelText("담당자 이메일")).toBeVisible();
    expect(screen.getByLabelText("고정 최종 승인자")).toBeVisible();
    expect(screen.getByLabelText("템플릿 키")).toBeVisible();
    expect(screen.getByLabelText("평일 알림 시각")).toBeVisible();
  });

  it("creates master data with the verified writer headers", async () => {
    const user = userEvent.setup();
    render(<AdminPage />);
    await user.click(screen.getByRole("button", { name: "관리 시작" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));
    await user.type(await screen.findByLabelText("고객사명"), "Acme");
    await user.click(screen.getByRole("button", { name: "고객사 추가" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/admin/master-data/customers",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Writer-Name": "Kim",
          "X-Writer-Password": "correct-password",
        },
        body: JSON.stringify({ name: "Acme", active: true }),
      },
    ));
  });

  it("closes the management screen when WriterGate clears its credential", async () => {
    const user = userEvent.setup();
    render(<AdminPage />);
    await user.click(screen.getByRole("button", { name: "관리 시작" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));
    expect(await screen.findByLabelText("고객사명")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "작성자 변경" }));

    expect(screen.queryByLabelText("고객사명")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "관리 시작" })).toBeVisible();
  });

  it("binds the loaded final approver and notification time", async () => {
    const user = userEvent.setup();
    render(<AdminPage />);
    await user.click(screen.getByRole("button", { name: "관리 시작" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(await screen.findByLabelText("고정 최종 승인자")).toHaveValue("8");
    expect(screen.getByLabelText("평일 알림 시각")).toHaveValue("08:30");
  });

  it("announces an async save and prevents repeated submission", async () => {
    let resolvePost!: (response: Response) => void;
    const pendingPost = new Promise<Response>((resolve) => { resolvePost = resolve; });
    let customerPosts = 0;
    fetchMock.mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/writer/verify")) return jsonResponse({ writer_name: "Kim" });
      if (url.endsWith("/customers") && init?.method === "POST") {
        customerPosts += 1;
        return pendingPost;
      }
      return jsonResponse([]);
    });
    const user = userEvent.setup();
    render(<AdminPage />);
    await user.click(screen.getByRole("button", { name: "관리 시작" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));
    await user.type(await screen.findByLabelText("고객사명"), "Acme");

    const saveButton = screen.getByRole("button", { name: "고객사 추가" });
    await user.click(saveButton);
    await user.click(saveButton);

    expect(saveButton).toBeDisabled();
    expect(screen.getByText("저장 중입니다.").closest("[role='status']")).toHaveAttribute("aria-live", "polite");
    expect(customerPosts).toBe(1);

    resolvePost(jsonResponse({ id: 2, name: "Acme", active: true }, 201));
    expect(await screen.findByText("저장했습니다.")).toBeVisible();
    expect(saveButton).toBeEnabled();
  });
});
