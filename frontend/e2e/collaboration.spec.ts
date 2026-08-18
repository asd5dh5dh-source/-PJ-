import { expect, test } from "@playwright/test";

const draft = {
  id: 1,
  case_id: "VOC-2026-0001",
  round_number: 1,
  stage: "received",
  customer_request: "Investigate gas generation",
  original_mail_body: "From: Jane Doe <jane@example.com>",
  priority: "high",
  tasks: [],
  reviews: [],
};

const notificationPreview = {
  id: 1,
  recipients: ["owner@example.com"],
  subject: "[VOC-2026-0001] assignment preview",
  body: "Quality assignment is ready for review.",
  scheduled_at: "2026-08-18T09:00:00+09:00",
  sent_at: null,
  runtime_profile: "external_review",
  delivery_status: "preview",
  real_delivery: false,
  created_at: "2026-08-18T09:00:00+09:00",
};

test("writer can save a draft and inspect notification preview", async ({ page }) => {
  const protectedWrites: Array<{ url: string; headers: Record<string, string> }> = [];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());

    if (request.method() === "POST" && url.pathname === "/api/writer/verify") {
      await route.fulfill({ json: { writer_name: "QA Writer" } });
      return;
    }
    if (request.method() === "POST" && url.pathname === "/api/voc") {
      protectedWrites.push({ url: url.pathname, headers: request.headers() });
      await route.fulfill({ status: 201, json: draft });
      return;
    }
    if (request.method() === "GET" && url.pathname === "/api/archive") {
      await route.fulfill({
        json: { items: [], total: 0, page: 1, page_size: 20, sort: "relevance" },
      });
      return;
    }
    if (request.method() === "GET" && url.pathname === "/api/notifications") {
      await route.fulfill({ json: [notificationPreview] });
      return;
    }
    await route.fulfill({ status: 405, json: { detail: "Unexpected mocked request" } });
  });

  await page.goto("/requests/new");
  await page.locator('textarea[name="original_mail_body"]').fill(
    "From: Jane Doe <jane@example.com>\nCompany: Example Materials\n\nPlease investigate.",
  );
  await page.locator('form button[type="button"]').first().click();
  await page.locator('select[name="voc_type"]').selectOption("Inquiry");
  await page.locator('input[name="voc_subtype"]').fill("Gas Generation");
  await page.locator('textarea[name="customer_request"]').fill("Investigate gas generation");
  await page.locator('input[name="task_department_0"]').fill("Quality");
  await page.locator('form button[type="submit"]').click();

  const writerDialog = page.getByRole("dialog");
  await writerDialog.locator('input[name="writer_name"]').fill("QA Writer");
  await writerDialog.locator('input[name="password"]').fill("test-password");
  await writerDialog.locator('button[type="submit"]').click();

  await expect(page.getByRole("heading", { name: /VOC-2026-0001/ })).toBeVisible();
  expect(protectedWrites).toHaveLength(1);
  expect(protectedWrites[0].headers["x-writer-name"]).toBe("QA Writer");
  expect(protectedWrites[0].headers["x-writer-password"]).toBe("test-password");

  await page.goto("/notifications");
  await expect(page.getByText(notificationPreview.subject)).toBeVisible();
  await page.locator("article").filter({ hasText: notificationPreview.subject }).locator("summary").click();
  await expect(page.getByText(notificationPreview.body)).toBeVisible();
});
