import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import NewRequestPage from "./page";

const savedCase = {
  case_id: "WEB-ABC123ABC123",
  customer_name: "Sample Customer",
  product_equipment: "NCA",
  voc_type: "Inquiry",
  voc_subtype: "Gas Generation",
  customer_request: "Investigate gas generation",
  responsible_departments: "Quality",
  received_at: "2026-08-18",
  final_status: "received",
  record_origin: "user_input",
  bm25_score: null,
  final_score: null,
  matched_keywords: [],
  original_mail_body: "Gas generation inquiry...",
  full_response_history: null,
};

const similarCases = {
  items: [1, 2, 3].map((number) => ({
    case_id: `CLOSED-${number}`,
    customer_name: `Customer ${number}`,
    product_equipment: "NCA",
    voc_type: "Inquiry",
    voc_subtype: "Gas Generation",
    customer_request: `Closed gas investigation ${number}`,
    responsible_departments: "Quality",
    received_at: `2026-0${number}-01`,
    final_status: "closed",
    record_origin: "historical",
    bm25_score: 4 - number,
    final_score: 4.4 - number,
    matched_keywords: ["gas", "generation"],
  })),
};

function jsonResponse(body: unknown, ok = true) {
  return { ok, status: ok ? 200 : 500, json: vi.fn().mockResolvedValue(body) } as unknown as Response;
}

describe("new request workflow", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("saves a manually entered request and shows top three closed cases", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(savedCase)).mockResolvedValueOnce(jsonResponse(similarCases));
    const user = userEvent.setup();

    render(<NewRequestPage />);
    expect(screen.getByRole("link", { name: "신규 요청" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "VOC 아카이브" })).not.toHaveAttribute("aria-current");
    await user.type(screen.getByLabelText("원본 메일"), "Gas generation inquiry...");
    await user.type(screen.getByLabelText("고객명"), "Sample Customer");
    await user.selectOptions(screen.getByLabelText("VOC Type"), "Inquiry");
    await user.type(screen.getByLabelText("VOC Subtype"), "Gas Generation");
    await user.type(screen.getByLabelText("고객 요청"), "Investigate gas generation");
    await user.type(screen.getByLabelText("제품 / 설비"), "NCA");
    await user.type(screen.getByLabelText("담당 부서"), "Quality");
    await user.click(screen.getByRole("button", { name: "저장 및 유사 사례 검색" }));

    expect(await screen.findAllByTestId("similar-case")).toHaveLength(3);
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/requests", expect.objectContaining({
      method: "POST",
      body: JSON.stringify({
        customer_name: "Sample Customer",
        product_equipment: "NCA",
        voc_type: "Inquiry",
        voc_subtype: "Gas Generation",
        customer_request: "Investigate gas generation",
        original_mail_body: "Gas generation inquiry...",
        responsible_departments: "Quality",
      }),
    }));
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/requests/WEB-ABC123ABC123/similar-cases",
      { signal: expect.any(AbortSignal) },
    );
    expect(screen.getByRole("link", { name: "CLOSED-1 상세 보기" })).toHaveAttribute("href", "/archive?case_id=CLOSED-1");
    expect(screen.getAllByText("gas")).toHaveLength(3);
    expect(screen.getByText("상대 점수 3.4")).toBeInTheDocument();
    expect(screen.getByText("Customer 1")).toBeInTheDocument();
    expect(screen.getAllByText("NCA")).toHaveLength(3);
    expect(screen.getAllByText("Inquiry / Gas Generation")).toHaveLength(3);
    expect(screen.getByText("Closed gas investigation 1")).toBeInTheDocument();
    expect(screen.getAllByText("Quality")).toHaveLength(3);
    expect(screen.getByText("2026-01-01")).toBeInTheDocument();
  });

  it("keeps entered values when saving fails", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: "failed" }, false));
    const user = userEvent.setup();

    render(<NewRequestPage />);
    await user.type(screen.getByLabelText("원본 메일"), "Mail to keep");
    await user.type(screen.getByLabelText("고객명"), "Customer to keep");
    await user.selectOptions(screen.getByLabelText("VOC Type"), "Complaint");
    await user.type(screen.getByLabelText("VOC Subtype"), "Subtype to keep");
    await user.type(screen.getByLabelText("고객 요청"), "Request to keep");
    await user.click(screen.getByRole("button", { name: "저장 및 유사 사례 검색" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("저장하지 못했습니다");
    expect(screen.getByLabelText("원본 메일")).toHaveValue("Mail to keep");
    expect(screen.getByLabelText("고객명")).toHaveValue("Customer to keep");
  });

  it("disables submission while the save is pending", async () => {
    let resolveSave!: (response: Response) => void;
    fetchMock.mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve; }));
    const user = userEvent.setup();

    render(<NewRequestPage />);
    await user.type(screen.getByLabelText("원본 메일"), "Pending mail");
    await user.type(screen.getByLabelText("고객명"), "Pending customer");
    await user.selectOptions(screen.getByLabelText("VOC Type"), "Request");
    await user.type(screen.getByLabelText("VOC Subtype"), "Pending subtype");
    await user.type(screen.getByLabelText("고객 요청"), "Pending request");
    await user.click(screen.getByRole("button", { name: "저장 및 유사 사례 검색" }));

    const pendingButton = screen.getByRole("button", { name: "저장 중..." });
    expect(pendingButton).toBeDisabled();
    await user.click(pendingButton);
    expect(fetchMock).toHaveBeenCalledTimes(1);

    resolveSave(jsonResponse(savedCase));
  });

  it("retries a failed similar-case lookup without clearing the entered request", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(savedCase))
      .mockResolvedValueOnce(jsonResponse({ detail: "failed" }, false))
      .mockResolvedValueOnce(jsonResponse(similarCases));
    const user = userEvent.setup();

    render(<NewRequestPage />);
    await user.type(screen.getByLabelText("원본 메일"), "Mail to preserve");
    await user.type(screen.getByLabelText("고객명"), "Customer to preserve");
    await user.selectOptions(screen.getByLabelText("VOC Type"), "Inquiry");
    await user.type(screen.getByLabelText("VOC Subtype"), "Gas Generation");
    await user.type(screen.getByLabelText("고객 요청"), "Request to preserve");
    await user.click(screen.getByRole("button", { name: "저장 및 유사 사례 검색" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("유사 사례를 불러오지 못했습니다");
    expect(screen.getByLabelText("원본 메일")).toHaveValue("Mail to preserve");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(await screen.findAllByTestId("similar-case")).toHaveLength(3);
  });
});
