import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ArchivePage from "./page";

const archiveItem = {
  case_id: "COM-001",
  customer_name: "Alpha",
  product_equipment: "NCM811",
  voc_type: "Complaint",
  voc_subtype: "Cell Low Voltage",
  customer_request: "Cell low voltage alarm",
  responsible_departments: "Quality",
  received_at: "2026-01-02",
  final_status: "closed",
  record_origin: "historical",
  bm25_score: 2.25,
  final_score: 3.25,
  matched_keywords: ["gas", "generation"],
};

const archivePage = {
  items: [archiveItem],
  total: 1,
  page: 1,
  page_size: 20,
  sort: "relevance" as const,
};

const archiveDetail = {
  ...archiveItem,
  original_mail_body: "The cell voltage is below the requested level.",
  full_response_history: "Reviewed low voltage condition.",
};

describe("ArchivePage", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const data = url.includes("/COM-001")
          ? archiveDetail
          : { ...archivePage, sort: url.includes("q=") ? "relevance" : "latest" };
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  it("keeps URL-backed filters while opening and closing the preview", async () => {
    const user = userEvent.setup();
    render(<ArchivePage />);

    await user.type(screen.getByRole("searchbox"), "gas generation");
    await user.click(screen.getByRole("button", { name: "검색" }));
    await user.click(await screen.findByText("COM-001"));

    const preview = await screen.findByRole("complementary");
    expect(preview).toHaveTextContent("원본 메일");
    expect(screen.getByRole("searchbox")).toHaveValue("gas generation");
    expect(window.location.search).toContain("q=gas+generation");
    expect(window.location.search).toContain("case_id=COM-001");
    expect(within(preview).getByRole("link", { name: "상세 화면에서 보기" })).toHaveAttribute(
      "href",
      "/archive/COM-001?return_to=%2Farchive%3Fq%3Dgas%2Bgeneration%26sort%3Drelevance",
    );

    await user.click(within(preview).getByRole("button", { name: "미리보기 닫기" }));
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(window.location.search).toBe("?q=gas+generation&sort=relevance");
  });

  it("restores filters and pagination from browser popstate", async () => {
    window.history.replaceState({}, "", "/archive?q=gas+generation");
    render(<ArchivePage />);

    expect(await screen.findByRole("searchbox")).toHaveValue("gas generation");

    window.history.pushState({}, "", "/archive?q=cell+voltage&page=2");
    window.dispatchEvent(new PopStateEvent("popstate"));

    await waitFor(() => expect(screen.getByRole("searchbox")).toHaveValue("cell voltage"));
    await waitFor(() => expect(String(vi.mocked(fetch).mock.calls.at(-1)?.[0])).toContain("page=2"));
  });

  it("keeps the selected case while changing pages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const page = Number(new URL(url, "http://localhost").searchParams.get("page") ?? 1);
        const data = url.includes("/COM-001")
          ? archiveDetail
          : { ...archivePage, total: 40, page };
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
    const user = userEvent.setup();
    render(<ArchivePage />);

    await user.click(await screen.findByText("COM-001"));
    await user.click(await screen.findByRole("button", { name: "다음" }));

    expect(window.location.search).toContain("page=2");
    expect(window.location.search).toContain("case_id=COM-001");
    expect(await screen.findByRole("complementary")).toHaveAccessibleName("COM-001 사례 미리보기");
  });

  it("does not claim that case IDs are part of full-text search", () => {
    render(<ArchivePage />);

    expect(screen.getByRole("searchbox")).toHaveAttribute(
      "placeholder",
      "요청 내용, 키워드 검색",
    );
  });

  it("offers relevance sorting only for keyword searches", async () => {
    const user = userEvent.setup();
    render(<ArchivePage />);

    const sort = await screen.findByRole("combobox", { name: "정렬" });
    expect(within(sort).queryByRole("option", { name: "관련도순" })).not.toBeInTheDocument();

    await user.type(screen.getByRole("searchbox"), "gas");
    await user.click(screen.getByRole("button", { name: "검색" }));

    expect(within(screen.getByRole("combobox", { name: "정렬" })).getByRole("option", { name: "관련도순" })).toBeInTheDocument();
  });

  it("keeps draft filters when changing the result sort", async () => {
    const user = userEvent.setup();
    render(<ArchivePage />);

    await user.click(screen.getByText("상세 필터"));
    await user.type(screen.getByRole("textbox", { name: "고객사" }), "Alpha");
    await user.selectOptions(await screen.findByRole("combobox", { name: "정렬" }), "oldest");

    expect(window.location.search).toBe("?customer_name=Alpha&sort=oldest");
    expect(screen.getByRole("textbox", { name: "고객사" })).toHaveValue("Alpha");
  });

  it("shows a retryable error instead of stale results", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("bad gateway", { status: 502 })));

    render(<ArchivePage />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("검색 결과를 불러오지 못했습니다.");
    expect(within(alert).getByRole("button", { name: "다시 시도" })).toBeInTheDocument();
    expect(screen.queryByText("COM-001")).not.toBeInTheDocument();
  });

  it("writer-gates archive exports and preserves the active filters", async () => {
    const user = userEvent.setup();
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:archive"),
      revokeObjectURL: vi.fn(),
    });
    vi.mocked(fetch).mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/writer/verify")) {
        return new Response(JSON.stringify({ writer_name: "Kim" }), { status: 200 });
      }
      if (url.includes("/api/export/archive.csv")) return new Response("case_id\nCOM-001", { status: 200 });
      const data = url.includes("/COM-001")
        ? archiveDetail
        : { ...archivePage, sort: url.includes("q=") ? "relevance" : "latest" };
      return new Response(JSON.stringify(data), { status: 200, headers: { "Content-Type": "application/json" } });
    });

    render(<ArchivePage />);
    await user.type(screen.getByRole("searchbox"), "gas generation");
    await user.click(screen.getByRole("button", { name: "검색" }));
    await user.click(screen.getByRole("button", { name: "CSV 다운로드" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(
      "/api/export/archive.csv?q=gas+generation&sort=relevance",
      { headers: { "X-Writer-Name": "Kim", "X-Writer-Password": "correct-password" } },
    ));
    expect(click).toHaveBeenCalled();
  });
});
