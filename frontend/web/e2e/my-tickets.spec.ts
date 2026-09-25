import { expect, test } from "@playwright/test";

const SESSION = {
  state: {
    userId: "u1",
    email: "e2e@example.com",
    roles: ["USER"],
    accessToken: "e2e-token",
  },
  version: 0,
};

const reservation = (status: "CONFIRMED" | "CANCELLED") => ({
  reservationId: "res-1",
  userId: "u1",
  eventId: "evt1",
  seatId: "seat-1",
  status,
  qrCode: status === "CONFIRMED" ? "QR-CODE-1" : null,
  reservedAt: new Date().toISOString(),
  expiresAt: new Date(Date.now() + 900_000).toISOString(),
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript((session) => {
    window.sessionStorage.setItem("trueticket-session", JSON.stringify(session));
  }, SESSION);
});

test("cancels a reservation only after confirming the dialog", async ({ page }) => {
  let status: "CONFIRMED" | "CANCELLED" = "CONFIRMED";

  await page.route("**/api/reservations", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([reservation(status)]),
    });
  });

  let cancelRequests = 0;
  await page.route("**/api/reservations/res-1/cancel", async (route) => {
    cancelRequests += 1;
    status = "CANCELLED";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(reservation(status)),
    });
  });

  await page.goto("/my-tickets");
  await expect(page.getByText("QR-CODE-1")).toBeVisible();

  await page.getByRole("button", { name: "예매 취소" }).click();
  await expect(page.getByText("예매를 취소할까요?")).toBeVisible();
  expect(cancelRequests).toBe(0);

  await page.getByRole("button", { name: "네, 취소합니다" }).click();

  await expect(page.getByText("취소됨")).toBeVisible();
  await expect(page.getByRole("button", { name: "예매 취소" })).toHaveCount(0);
  expect(cancelRequests).toBe(1);
});

test("closing the dialog without confirming does not cancel the reservation", async ({ page }) => {
  await page.route("**/api/reservations", async (route) => {
    if (route.request().method() !== "GET") return route.fallback();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([reservation("CONFIRMED")]),
    });
  });

  let cancelRequests = 0;
  await page.route("**/api/reservations/res-1/cancel", async (route) => {
    cancelRequests += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(reservation("CANCELLED")),
    });
  });

  await page.goto("/my-tickets");
  await page.getByRole("button", { name: "예매 취소" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "닫기", exact: true }).click();

  await expect(page.getByText("예매를 취소할까요?")).not.toBeVisible();
  expect(cancelRequests).toBe(0);
});
