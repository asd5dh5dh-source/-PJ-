import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ArchiveDetailContent, safeArchiveReturnTo } from "./page";

const detail = {
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
  bm25_score: null,
  final_score: null,
  matched_keywords: [],
  original_mail_body: "Original customer mail",
  full_response_history: "Response history",
};

describe("archive detail page", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(detail), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => vi.unstubAllGlobals());

  it("fetches the selected detail and restores an encoded archive location", async () => {
    render(
      <ArchiveDetailContent
        caseId="COM-001"
        returnTo="/archive?q=gas+generation&sort=relevance&page=2"
      />,
    );

    expect(await screen.findByRole("heading", { name: "COM-001" })).toBeInTheDocument();
    expect(await screen.findByText("Original customer mail")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "검색 결과로 돌아가기" })).toHaveAttribute(
      "href",
      "/archive?q=gas+generation&sort=relevance&page=2",
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/archive/COM-001",
      { signal: expect.any(AbortSignal) },
    );
  });

  it.each([
    "https://attacker.example/archive?q=secret",
    "//attacker.example/archive",
    "/requests/new",
    "/archive/COM-001",
  ])("falls back for unsafe return_to value %s", (value) => {
    expect(safeArchiveReturnTo(value)).toBe("/archive");
  });
});
