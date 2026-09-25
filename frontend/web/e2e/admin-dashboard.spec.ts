import { expect, test } from "@playwright/test";

const listings = [
  {
    listingId: "l1",
    sellerId: "se1",
    platformName: "번개장터",
    eventTitleMatched: "IU 콘서트",
    listedPrice: 150000,
    priceAnomalyScore: 0.8,
  },
  {
    listingId: "l2",
    sellerId: "se2",
    platformName: "중고나라",
    eventTitleMatched: "IU 콘서트",
    listedPrice: 200000,
    priceAnomalyScore: 0.3,
  },
  {
    listingId: "l3",
    sellerId: "se1",
    platformName: "번개장터",
    eventTitleMatched: "야구 결승",
    listedPrice: 90000,
    priceAnomalyScore: 0,
  },
];

test("dashboard renders per-platform charts derived from the listings actually returned", async ({
  page,
}) => {
  await page.route("**/api/resale-monitor/listings", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(listings) });
  });

  await page.goto("/admin/dashboard");

  await expect(page.getByText("수집된 게시물").locator("..").getByText("3", { exact: true })).toBeVisible();
  // 이상 가격 의심: priceAnomalyScore > 0 인 게시물 2건(l1, l2).
  await expect(page.getByText("이상 가격 의심").locator("..").getByText("2", { exact: true })).toBeVisible();

  // 두 차트 각각 플랫폼 두 곳(번개장터, 중고나라)만큼의 막대가 그려져야 한다.
  const countChart = page.locator("text=플랫폼별 게시물 수").locator("..").locator(".recharts-bar-rectangle");
  await expect(countChart).toHaveCount(2);

  const scoreChart = page
    .locator("text=플랫폼별 평균 이상치 스코어")
    .locator("..")
    .locator(".recharts-bar-rectangle");
  await expect(scoreChart).toHaveCount(2);

  await expect(page.getByText("번개장터").first()).toBeVisible();
  await expect(page.getByText("중고나라").first()).toBeVisible();
});
