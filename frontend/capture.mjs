import { chromium } from "@playwright/test";
import fs from "node:fs";
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto("http://127.0.0.1:8000");
await page
  .getByLabel("Email", { exact: true })
  .fill(process.env.ADMIN_EMAIL || "jayden@example.com");
await page
  .getByLabel("Password", { exact: true })
  .fill(process.env.ADMIN_PASSWORD || "Local-demo-pass-2026");
await page.getByRole("button", { name: "Sign in", exact: true }).click();
await page.getByRole("heading", { name: "Operations overview" }).waitFor();
await page.waitForTimeout(2500);
fs.mkdirSync("../docs/screenshots", { recursive: true });
await page.screenshot({
  path: "../docs/screenshots/overview.png",
  fullPage: true,
});
await page.getByRole("button", { name: "Orders", exact: true }).click();
await page.getByRole("button", { name: "ORD-1001", exact: true }).click();
await page.getByRole("dialog").waitFor();
await page.waitForTimeout(500);
await page.screenshot({
  path: "../docs/screenshots/order-delivery.png",
  fullPage: true,
});
await page.getByRole("button", { name: "Close dialog" }).click();
await page.getByRole("button", { name: "Payments", exact: true }).click();
await page
  .getByLabel("Payment CSV")
  .setInputFiles("public/sample-payments.csv");
await page.getByText("PAY-2001", { exact: true }).waitFor();
await page.screenshot({
  path: "../docs/screenshots/reconciliation.png",
  fullPage: true,
});
await page.setViewportSize({ width: 390, height: 844 });
await page.screenshot({
  path: "../docs/screenshots/mobile-payments.png",
  fullPage: true,
});
await browser.close();
if (errors.length) throw new Error(errors.join("\n"));
console.log("Screenshots captured; no browser runtime errors.");
