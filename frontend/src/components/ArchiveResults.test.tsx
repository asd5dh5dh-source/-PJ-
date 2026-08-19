import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ArchiveResults from "./ArchiveResults";

describe("ArchiveResults", () => {
  it("links a current VOC result directly to its management workspace", () => {
    render(
      <ArchiveResults
        loading={false}
        error={false}
        onPage={vi.fn()}
        onRetry={vi.fn()}
        onSelect={vi.fn()}
        data={{
          items: [{
            case_id: "VOC-2026-0001",
            customer_name: "Current Customer",
            product_equipment: "NCM811",
            voc_type: "Complaint",
            voc_subtype: "Packing Damage",
            customer_request: "Containment plan",
            responsible_departments: "Quality",
            received_at: "2026-03-01",
            final_status: "received",
            record_origin: "current",
            bm25_score: null,
            final_score: null,
            matched_keywords: [],
          }],
          total: 1,
          page: 1,
          page_size: 20,
          sort: "latest",
        }}
      />,
    );

    expect(screen.getByRole("link", { name: "VOC-2026-0001 관리 화면" })).toHaveAttribute("href", "/voc/VOC-2026-0001");
  });
});
