import { expect, test } from "@playwright/test";

test.use({
  channel: "msedge",
  viewport: { width: 1980, height: 1250 },
});

test("Sprint 2 dashboard controls, insights, and query flow", async ({ page }) => {
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });

  await expect(page.getByText("GitHub Follower Intelligence")).toBeVisible();

  const header = page.locator("header");
  await header.getByRole("button", { name: "7D" }).click();
  await expect(header.getByRole("button", { name: "7D" })).toHaveAttribute("aria-pressed", "true");

  await header.getByRole("button", { name: "Delta" }).click();
  await expect(header.getByRole("button", { name: "Delta" })).toHaveAttribute("aria-pressed", "true");

  await header.getByRole("button", { name: "Compact" }).click();
  await expect(header.getByRole("button", { name: "Compact" })).toHaveAttribute("aria-pressed", "true");

  await page
    .getByPlaceholder("Ask about churn, high-signal followers, movement, or data health")
    .fill("Who are the most important new followers?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText("important followers")).toBeVisible();
  await expect(page.getByText("Recommended next actions")).toBeVisible();

  await page.getByRole("button", { name: /Refresh insights|Generate brief/ }).click();
  await expect(page.getByText("Grounded narrative")).toBeVisible();
  await expect(page.getByText("Evidence").first()).toBeVisible();
  await expect(page.getByText("Building a data-grounded summary")).toBeHidden({ timeout: 30000 });

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "../docs/screenshots/dashboard.png", fullPage: true });

  await page.getByTestId("chart-card").screenshot({
    path: "../docs/screenshots/dashboard-detail.png",
  });
});
