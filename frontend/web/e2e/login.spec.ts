import { expect, test } from "@playwright/test";

test.describe("login", () => {
  test("shows validation errors when submitted empty", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "로그인" }).click();

    await expect(page.getByText("이메일을 입력하세요")).toBeVisible();
    await expect(page.getByText("비밀번호를 입력하세요")).toBeVisible();
  });

  test("logs in and redirects to /events on success", async ({ page }) => {
    await page.route("**/api/auth/login", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          accessToken: "e2e-token",
          tokenType: "Bearer",
          expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
          userId: "u1",
          email: "e2e@example.com",
          role: "USER",
        }),
      });
    });

    await page.goto("/login");
    await page.getByLabel("이메일").fill("e2e@example.com");
    await page.getByLabel("비밀번호").fill("password123");
    await page.getByRole("button", { name: "로그인" }).click();

    await expect(page).toHaveURL("/events");
  });

  test("shows an inline error when the login request fails", async ({ page }) => {
    await page.route("**/api/auth/login", async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ message: "unauthorized" }),
      });
    });

    await page.goto("/login");
    await page.getByLabel("이메일").fill("wrong@example.com");
    await page.getByLabel("비밀번호").fill("wrongpass");
    await page.getByRole("button", { name: "로그인" }).click();

    await expect(page.getByText("이메일 또는 비밀번호를 확인해주세요.")).toBeVisible();
    await expect(page).toHaveURL("/login");
  });
});
