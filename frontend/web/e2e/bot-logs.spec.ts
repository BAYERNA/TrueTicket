import { expect, test } from "@playwright/test";

const scores = [
  {
    scoreId: "s1",
    reservationSessionId: "sess-a",
    acquisitionFraudScore: 0.2,
    isFlagged: false,
    evaluatedAt: "2026-01-01T00:00:00Z",
    modelVersion: "v1",
    reviewLabel: null,
  },
  {
    scoreId: "s2",
    reservationSessionId: "sess-b",
    acquisitionFraudScore: 0.9,
    isFlagged: true,
    evaluatedAt: "2026-01-02T00:00:00Z",
    modelVersion: "v1",
    reviewLabel: null,
  },
];

test("bot-logs table sorts by score when the header is clicked", async ({ page }) => {
  await page.route("**/api/bot-detection/scores", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(scores) });
  });

  await page.goto("/admin/bot-logs");

  const rows = page.locator("tbody tr");
  await expect(rows).toHaveCount(2);
  // 초기 정렬은 평가 시각 내림차순 — sess-b(01-02)가 sess-a(01-01)보다 먼저 나와야 한다.
  await expect(rows.nth(0)).toContainText("sess-b");

  // 숫자 컬럼은 첫 클릭이 내림차순이라 sess-b(0.9)가 계속 위에 있다 — 실제로 정렬
  // 기준이 바뀌었는지는 두 번째 클릭(오름차순)에서 sess-a(0.2)가 올라오는 것으로 확인한다.
  await page.getByRole("button", { name: /취득 부정성 스코어/ }).click();
  await expect(rows.nth(0)).toContainText("sess-b");

  await page.getByRole("button", { name: /취득 부정성 스코어/ }).click();
  await expect(rows.nth(0)).toContainText("sess-a");
});
