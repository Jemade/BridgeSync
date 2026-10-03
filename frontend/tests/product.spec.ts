import { test, expect } from "@playwright/test";

test("sign in, create an order, inspect delivery, import payments and sign out", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.ADMIN_EMAIL || "jayden@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.ADMIN_PASSWORD || "Local-demo-pass-2026");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Orders", exact: true }).click();
  await page.getByRole("button", { name: "New order" }).click();
  const reference = "E2E-" + Date.now();
  await page.getByLabel("Order reference", { exact: true }).fill(reference);
  await page
    .getByLabel("Customer", { exact: true })
    .fill("Browser test customer");
  await page.getByLabel("Amount", { exact: true }).fill("42.50");
  await page.getByRole("button", { name: "Accept order" }).click();
  await page.getByLabel("Search orders").fill(reference);
  await expect(
    page.getByRole("button", { name: reference, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: reference, exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page
      .getByRole("group", { name: "Delivery summary" })
      .getByText("Synced", { exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Payments", exact: true }).click();
  await page.getByLabel("Payment CSV").setInputFiles({
    name: "payments.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "reference,order_reference,amount,currency\nPAY-" +
        reference +
        "," +
        reference +
        ",42.50,USD\n",
    ),
  });
  await expect(
    page.getByText("PAY-" + reference, { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Matched", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to your workspace" }),
  ).toBeVisible();
});

test("mobile navigation has no page overflow and dialog supports escape", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.ADMIN_EMAIL || "jayden@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.ADMIN_PASSWORD || "Local-demo-pass-2026");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Operations overview" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Orders", exact: true }).click();
  await page.getByRole("button", { name: "New order" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
});

test("permanent delivery failure can be recovered from the interface", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.ADMIN_EMAIL || "jayden@example.com");
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.ADMIN_PASSWORD || "Local-demo-pass-2026");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("button", { name: "Integrations", exact: true }).click();
  await page.getByLabel("Test mode").selectOption("reject");
  await page
    .getByRole("status")
    .filter({ hasText: "Test connector updated." })
    .waitFor();
  await page.getByRole("button", { name: "Orders", exact: true }).click();
  await page.getByRole("button", { name: "New order" }).click();
  const reference = "RECOVERY-" + Date.now();
  await page.getByLabel("Order reference", { exact: true }).fill(reference);
  await page
    .getByLabel("Customer", { exact: true })
    .fill("Failure recovery test");
  await page.getByLabel("Amount", { exact: true }).fill("77.00");
  await page.getByRole("button", { name: "Accept order" }).click();
  await page.getByLabel("Search orders").fill(reference);
  await page.getByRole("button", { name: reference, exact: true }).click();
  await expect(
    page
      .getByRole("group", { name: "Delivery summary" })
      .getByText("Failed", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: "Integrations", exact: true }).click();
  await page.getByLabel("Test mode").selectOption("available");
  await page
    .getByRole("status")
    .filter({ hasText: "Test connector updated." })
    .waitFor();
  await page.getByRole("button", { name: "Orders", exact: true }).click();
  await page.getByLabel("Search orders").fill(reference);
  await page.getByRole("button", { name: reference, exact: true }).click();
  await page.getByRole("button", { name: "Retry delivery" }).click();
  await expect(
    page
      .getByRole("group", { name: "Delivery summary" })
      .getByText("Synced", { exact: true }),
  ).toBeVisible({ timeout: 15000 });
});
