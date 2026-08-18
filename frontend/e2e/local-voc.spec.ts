import { expect, test } from "@playwright/test";

const archiveItem = {
  case_id: "REQ-GAS",
  customer_name: "Battery Customer",
  product_equipment: "NCA",
  voc_type: "Inquiry",
  voc_subtype: "Gas Generation",
  customer_request: "Gas generation during storage",
  responsible_departments: "Engineering",
  received_at: "2026-02-03",
  final_status: "closed",
  record_origin: "historical",
  bm25_score: 2.5,
  final_score: 2.75,
  matched_keywords: ["gas", "generation"],
};

test("training archive can be searched without creating records", async ({ page }) => {
  const writeRequests: string[] = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    if (request.method() !== "GET") {
      writeRequests.push(request.method());
      await route.fulfill({ status: 405 });
      return;
    }

    const searched = new URL(request.url()).searchParams.has("q");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        items: [archiveItem],
        total: 1,
        page: 1,
        page_size: 20,
        sort: searched ? "relevance" : "latest",
      }),
    });
  });

  await page.goto("/archive");
  await page.getByRole("searchbox").fill("gas generation");
  await page.getByRole("button", { name: "검색" }).click();

  await expect(page.getByTestId("archive-result").first()).toBeVisible();
  await expect(page.getByText("관련도순", { exact: true }).last()).toBeVisible();
  expect(writeRequests).toEqual([]);
});
