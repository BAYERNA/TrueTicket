import { expect, test } from "@playwright/test";

const SESSION = {
  state: { userId: "u1", email: "e2e@example.com", roles: ["USER"], accessToken: "e2e-token" },
  version: 0,
};

const waitingStatus = { eventId: "evt1", userId: "u1", rank: 5, waitingCount: 42, admitted: false };

test.beforeEach(async ({ page }) => {
  await page.addInitScript((session) => {
    window.sessionStorage.setItem("trueticket-session", JSON.stringify(session));
  }, SESSION);
});

test("reserve view genuinely attempts a Socket.IO connection and falls back to REST polling when it fails", async ({
  page,
}) => {
  let socketRequestSeen = false;
  // queue-service에는 실제 Socket.IO 서버가 없다 — 연결이 시도된 뒤 거부되는 실제 상황을
  // 그대로 재현하기 위해 접속을 abort한다(가짜로 성공시키지 않는다).
  await page.route("**/socket.io/**", async (route) => {
    socketRequestSeen = true;
    await route.abort("connectionrefused");
  });

  await page.route("**/api/queue/evt1/join", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(waitingStatus),
    });
  });
  await page.route("**/api/queue/evt1/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(waitingStatus),
    });
  });

  await page.goto("/events/evt1/reserve");

  await expect(page.getByText(/대기 중입니다/)).toBeVisible();
  await expect(page.getByText("현재 순번: 5", { exact: false })).toBeVisible();

  // 연결이 정직하게 실패로 귀결되고, 폴링이 폴백으로 살아있음을 확인한다.
  await expect(page.getByText("실시간 연결 불가 — 3초마다 자동 갱신 중")).toBeVisible({ timeout: 15000 });
  expect(socketRequestSeen).toBe(true);
});
