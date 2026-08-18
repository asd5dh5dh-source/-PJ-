import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { VocDetailContent } from "./page";

const detail = {
  case_id: "VOC-2026-0001",
  rounds: [
    {
      id: 1,
      case_id: "VOC-2026-0001",
      round_number: 1,
      customer_request: "Investigate gas generation",
      original_mail_body: "Original mail",
      sender_name: "Jane Doe",
      sender_email: "jane@example.com",
      sender_company: "Example Materials",
      translation_draft: "가스 발생 원인을 조사하고 있습니다.",
      translation_final: null,
      voc_type: "Inquiry",
      voc_subtype: "Gas Generation",
      product_equipment: "NCA",
      priority: "high",
      stage: "in_progress",
      created_by: "Kim",
      created_at: "2026-08-18T01:00:00Z",
      updated_at: "2026-08-18T02:00:00Z",
      tasks: [
        {
          id: 7,
          voc_request_id: 1,
          department: "품질",
          assignee_name: "Lee",
          assignee_email: "lee@example.com",
          manager_name: "Kim",
          manager_email: "kim@example.com",
          status: "in_progress",
          response_content: "원인 분석 중",
          due_date: "2026-08-20",
          delay_reason: null,
          ecm_link: "https://ecm.example/doc/7",
          revision: 0,
        },
      ],
      reviews: [],
      stage_history: [
        {
          id: 1,
          voc_request_id: 1,
          from_stage: "managing",
          to_stage: "in_progress",
          reason: null,
          ecm_link: null,
          changed_by: "Kim",
          changed_at: "2026-08-18T02:00:00Z",
        },
      ],
    },
  ],
  audits: [
    {
      id: 1,
      entity_type: "department_task",
      entity_id: "7",
      action: "updated",
      writer_name: "Kim",
      changed_at: "2026-08-18T02:00:00Z",
    },
  ],
};

const refreshedDetail = {
  ...detail,
  rounds: [{
    ...detail.rounds[0],
    stage: "department_work",
    tasks: [{
      ...detail.rounds[0].tasks[0],
      status: "completed",
      response_content: "조치 완료",
      due_date: "2026-08-21",
      revision: 1,
    }],
  }],
};

const twoTaskDetail = {
  ...detail,
  rounds: [{
    ...detail.rounds[0],
    tasks: [
      detail.rounds[0].tasks[0],
      {
        ...detail.rounds[0].tasks[0],
        id: 8,
        department: "기술",
        assignee_name: "Park",
        manager_name: "Choi",
        ecm_link: null,
      },
    ],
  }],
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("VOC detail page", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("shows task status separately from the overall VOC stage", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(detail));

    render(<VocDetailContent caseId="VOC-2026-0001" />);

    expect(await screen.findByText("전체 단계: 대응 중")).toBeVisible();
    expect(screen.getByText("품질 · 조치 중")).toBeVisible();
    expect(screen.getByRole("heading", { name: "1차 요청" })).toBeVisible();
    expect(screen.getByText("관리 중 → 대응 중")).toBeVisible();
    expect(screen.getByText("가스 발생 원인을 조사하고 있습니다.")).toBeVisible();
    expect(screen.getByRole("link", { name: "품질 ECM 문서" })).toHaveAttribute(
      "href",
      "https://ecm.example/doc/7",
    );
    expect(screen.getByText("Kim · updated")).toBeVisible();
  });

  it("writer-gates department approval and sends protected headers", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(detail))
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse({ id: 3, decision: "approved" }, 201))
      .mockResolvedValueOnce(jsonResponse(detail));
    const user = userEvent.setup();

    render(<VocDetailContent caseId="VOC-2026-0001" />);
    await screen.findByText("품질 · 조치 중");
    await user.click(screen.getByRole("button", { name: "품질 부서 승인" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/tasks/7/review", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Writer-Name": "Kim",
        "X-Writer-Password": "correct-password",
      },
      body: JSON.stringify({
        reviewer_role: "department_manager",
        decision: "approved",
      }),
    });
  });

  it("refreshes controlled task and stage fields after detail reload", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(detail))
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Kim" }))
      .mockResolvedValueOnce(jsonResponse({ id: 3, decision: "approved" }, 201))
      .mockResolvedValueOnce(jsonResponse(refreshedDetail));
    const user = userEvent.setup();

    render(<VocDetailContent caseId="VOC-2026-0001" />);
    await screen.findByText("품질 · 조치 중");
    await user.click(screen.getByRole("button", { name: "품질 부서 승인" }));
    await user.type(screen.getByLabelText("작성자명"), "Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(await screen.findByText("전체 단계: 부서별 검토 요청")).toBeVisible();
    expect(screen.getByLabelText("과제 상태")).toHaveValue("completed");
    expect(screen.getByLabelText("대응 내용")).toHaveValue("조치 완료");
    expect(screen.getByLabelText("완료 예정일")).toHaveValue("2026-08-21");
    expect(screen.getByLabelText("전체 단계")).toHaveValue("department_work");
  });

  it("targets the selected task for final rejection", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(twoTaskDetail))
      .mockResolvedValueOnce(jsonResponse({ writer_name: "Final Kim" }))
      .mockResolvedValueOnce(jsonResponse({ id: 4, decision: "rejected" }, 201))
      .mockResolvedValueOnce(jsonResponse(twoTaskDetail));
    const user = userEvent.setup();

    render(<VocDetailContent caseId="VOC-2026-0001" />);
    await screen.findByText("기술 · 조치 중");
    await user.selectOptions(screen.getByLabelText("최종 승인 대상 과제"), "8");
    await user.click(screen.getByRole("button", { name: "최종 반려" }));
    await user.type(screen.getByLabelText("작성자명"), "Final Kim");
    await user.type(screen.getByLabelText("공용 비밀번호"), "correct-password");
    await user.click(screen.getByRole("button", { name: "인증 후 계속" }));

    expect(fetchMock).toHaveBeenNthCalledWith(3, "/api/tasks/8/review", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Writer-Name": "Final Kim",
        "X-Writer-Password": "correct-password",
      },
      body: JSON.stringify({ reviewer_role: "final_approver", decision: "rejected" }),
    });
  });
});
