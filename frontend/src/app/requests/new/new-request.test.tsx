import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import NewRequestPage from "./page";

const draft = {
  id: 1,
  case_id: "VOC-2026-0001",
  round_number: 1,
  stage: "received",
  customer_request: "Investigate gas generation",
  original_mail_body: "From: Jane Doe <jane@example.com>",
  sender_name: "Jane Doe",
  sender_email: "jane@example.com",
  sender_company: "Example Materials",
  priority: "high",
  tasks: [{ id: 7, department: "Quality", status: "not_started" }],
  reviews: [],
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
  total: 3,
  page: 1,
  page_size: 20,
  sort: "relevance",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function fillRequest(user: ReturnType<typeof userEvent.setup>) {
  await user.type(
    screen.getByLabelText("원본 메일"),
    "From: Jane Doe <jane@example.com>{enter}Company: Example Materials{enter}{enter}Please investigate.",
  );
  await user.click(screen.getByRole("button", { name: "메일 내용 확인" }));
  await user.selectOptions(screen.getByLabelText("VOC Type"), "Inquiry");
  await user.type(screen.getByLabelText("VOC Subtype"), "Gas Generation");
  await user.type(screen.getByLabelText("제품 / 설비"), "NCA");
  await user.type(screen.getByLabelText("고객 요청"), "Investigate gas generation");
  await user.selectOptions(screen.getByLabelText("우선순위"), "high");
  await user.type(screen.getByLabelText("담당 부서 1"), "Quality");
  await user.type(screen.getByLabelText("담당자 1"), "Lee");
  await user.type(screen.getByLabelText("직책자 1"), "Kim");
  await user.type(screen.getByLabelText("완료 예정일 1"), "2026-08-20");
}

async function authenticate(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("작성자명"), "Kim");
  await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
  await user.click(screen.getByRole("button", { name: "인증 후 계속" }));
}

describe("new request collaboration workflow", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("requires writer verification before saving a draft", async () => {
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    await user.click(screen.getByRole("button", { name: "임시 저장" }));

    expect(await screen.findByLabelText("작성자명")).toBeVisible();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("confirms extracted mail fields, saves a server draft, and shows Top 3", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse(draft, 201))
      .mockResolvedValueOnce(jsonResponse(similarCases));
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    expect(screen.getByLabelText("발신자명")).toHaveValue("Jane Doe");
    expect(screen.getByLabelText("발신자 이메일")).toHaveValue("jane@example.com");
    expect(screen.getByLabelText("발신 회사")).toHaveValue("Example Materials");
    await user.click(screen.getByRole("button", { name: "임시 저장" }));
    await authenticate(user);

    expect(await screen.findByText("임시 저장됨: VOC-2026-0001")).toBeVisible();
    expect(await screen.findAllByTestId("similar-case")).toHaveLength(3);
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/voc", expect.objectContaining({
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Writer-Name": "Kim",
        "X-Writer-Password": "correct-password",
      },
      body: expect.stringContaining('"department":"Quality"'),
    }));
    expect(fetchMock.mock.calls[2]?.[0]).toContain("/api/archive?");
    const topThreeUrl = new URL(String(fetchMock.mock.calls[2]?.[0]), "http://frontend.local");
    expect(topThreeUrl.searchParams.get("q")).toBe(
      "Investigate gas generation\n\nFrom: Jane Doe <jane@example.com>\nCompany: Example Materials\n\nPlease investigate.",
    );
    expect(topThreeUrl.searchParams.get("voc_subtype")).toBe("Gas Generation");
    expect(topThreeUrl.searchParams.get("final_status")).toBe("closed");
    expect(screen.getByRole("link", { name: "VOC-2026-0001 관리 화면" })).toHaveAttribute(
      "href",
      "/voc/VOC-2026-0001",
    );
  });

  it("disables draft creation after the server assigns a case id", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse(draft, 201))
      .mockResolvedValueOnce(jsonResponse(similarCases));
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    await user.click(screen.getByRole("button", { name: "임시 저장" }));
    await authenticate(user);

    expect(await screen.findByText("임시 저장됨: VOC-2026-0001")).toBeVisible();
    expect(screen.getByRole("button", { name: "저장 완료" })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("keeps entered values when saving fails", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse({ detail: "failed" }, 500));
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    await user.click(screen.getByRole("button", { name: "임시 저장" }));
    await authenticate(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("저장하지 못했습니다");
    expect(screen.getByLabelText("고객 요청")).toHaveValue("Investigate gas generation");
  });

  it("rejects trimmed-empty required fields without opening writer verification", async () => {
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await user.type(screen.getByLabelText("원본 메일"), "Mail body");
    await user.click(screen.getByRole("button", { name: "메일 내용 확인" }));
    await user.selectOptions(screen.getByLabelText("VOC Type"), "Inquiry");
    await user.type(screen.getByLabelText("VOC Subtype"), "Gas Generation");
    await user.type(screen.getByLabelText("고객 요청"), "   ");
    await user.click(screen.getByRole("button", { name: "임시 저장" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("고객 요청");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("disables draft saving while the request is pending", async () => {
    let resolveSave!: (response: Response) => void;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve; }));
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    await user.click(screen.getByRole("button", { name: "임시 저장" }));
    await authenticate(user);

    expect(await screen.findByRole("button", { name: "저장 중..." })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    resolveSave(jsonResponse(draft, 201));
  });

  it("retries a failed Top 3 lookup without clearing the request", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse(draft, 201))
      .mockResolvedValueOnce(jsonResponse({ detail: "failed" }, 500))
      .mockResolvedValueOnce(jsonResponse(similarCases));
    const user = userEvent.setup();
    render(<NewRequestPage />);

    await fillRequest(user);
    await user.click(screen.getByRole("button", { name: "임시 저장" }));
    await authenticate(user);

    expect(await screen.findByRole("alert")).toHaveTextContent("유사 사례를 불러오지 못했습니다");
    expect(screen.getByLabelText("고객 요청")).toHaveValue("Investigate gas generation");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));
    expect(await screen.findAllByTestId("similar-case")).toHaveLength(3);
  });
});
