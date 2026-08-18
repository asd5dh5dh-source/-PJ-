import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import WriterGate from "./WriterGate";

describe("WriterGate", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("verifies a writer before running a protected action", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ writer_name: "Kim" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const action = vi.fn();
    const user = userEvent.setup();

    render(
      <WriterGate>
        {(requestWriter) => (
          <button type="button" onClick={() => requestWriter(action)}>보호 작업</button>
        )}
      </WriterGate>,
    );

    await user.click(screen.getByRole("button", { name: "보호 작업" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "secret");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(await screen.findByText("Kim 작성자로 인증됨")).toBeVisible();
    expect(action).toHaveBeenCalledWith({ writer_name: "Kim", password: "secret" });
    expect(fetchMock).toHaveBeenCalledWith("/api/writer/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ writer_name: "Kim", password: "secret" }),
    });
    expect(localStorage).toHaveLength(0);
    expect(sessionStorage).toHaveLength(0);
  });

  it("does not run the action when verification fails", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Invalid writer credentials" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const action = vi.fn();
    const user = userEvent.setup();

    render(
      <WriterGate>
        {(requestWriter) => (
          <button type="button" onClick={() => requestWriter(action)}>보호 작업</button>
        )}
      </WriterGate>,
    );

    await user.click(screen.getByRole("button", { name: "보호 작업" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "wrong");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("인증하지 못했습니다");
    expect(action).not.toHaveBeenCalled();
  });

  it("traps keyboard focus and restores the trigger when Escape closes", async () => {
    const action = vi.fn();
    const user = userEvent.setup();

    render(
      <WriterGate>
        {(requestWriter) => (
          <button type="button" onClick={() => requestWriter(action)}>보호 작업</button>
        )}
      </WriterGate>,
    );

    const trigger = screen.getByRole("button", { name: "보호 작업" });
    await user.click(trigger);
    const writerName = screen.getByLabelText("작성자명");
    expect(writerName).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("공용 비밀번호")).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "취소" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "인증 후 계속" })).toHaveFocus();
    await user.tab();
    expect(writerName).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(action).not.toHaveBeenCalled();
  });
});
