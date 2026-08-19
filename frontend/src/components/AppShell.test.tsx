import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AppShell from "./AppShell";

describe("AppShell", () => {
  it("presents the Korean VOC workspace identity and utility header", () => {
    render(<AppShell><p>내용</p></AppShell>);

    expect(screen.getByRole("link", { name: "고객 요청 대응 플랫폼 홈" })).toBeVisible();
    expect(screen.getByText("고객 요청 대응 플랫폼")).toBeVisible();
    expect(screen.getByText("운영 업무 공간")).toBeVisible();
  });
});
