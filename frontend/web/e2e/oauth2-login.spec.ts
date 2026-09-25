import { expect, test } from "@playwright/test";

test("login page links to the real Google OAuth2 authorization endpoint", async ({ page }) => {
  await page.goto("/login");

  const googleLink = page.getByRole("link", { name: "Google로 로그인" });
  await expect(googleLink).toHaveAttribute("href", "http://localhost:8080/oauth2/authorization/google");
});

test("oauth2 callback logs the user in from the redirect and lands on /events", async ({ page }) => {
  await page.route("**/api/events", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.goto(
    "/oauth2/callback?accessToken=e2e-google-token&userId=u1&email=google-user%40example.com&role=USER",
  );

  await expect(page).toHaveURL("/events");

  const session = await page.evaluate(() => window.sessionStorage.getItem("trueticket-session"));
  expect(session).not.toBeNull();
  const parsed = JSON.parse(session as string);
  expect(parsed.state.accessToken).toBe("e2e-google-token");
  expect(parsed.state.email).toBe("google-user@example.com");
});

test("oauth2 callback without the expected params sends the user back to /login", async ({ page }) => {
  await page.goto("/oauth2/callback?accessToken=incomplete-redirect");

  await expect(page).toHaveURL("/login");
});
