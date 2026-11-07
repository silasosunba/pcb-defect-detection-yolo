import { test, expect, type Page } from "@playwright/test";

const password = "Browser-test-password-123";

async function signIn(page: Page) {

  await page.goto("/auth/login");
  await page.getByLabel("Email", { exact: true }).fill("admin@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();

}

test("reference-style landing page, registration and missing-model state", async ({
  page,
}) => {

  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "PCB Defect Detector", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Advanced Features" }),
  ).toBeVisible();
  await expect(page.locator(".feature-card")).toHaveCount(6);
  await page.screenshot({
    path: "/private/tmp/pcb-detect-home.png",
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Start Analyzing", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "PCB Image Analysis" }),
  ).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/pcb-detect-analyze.png",
    fullPage: true,
  });
  await page.goto("/auth/register");
  await page.getByLabel("Full name").fill("Alex Inspector");
  const email = `inspector-${Date.now()}@example.com`;
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Dashboard", exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".desktop-nav").getByRole("link", { name: "Administration" }),
  ).toHaveCount(0);
  await page
    .locator(".desktop-nav")
    .getByRole("link", { name: "Analyze", exact: true })
    .click();
  await expect(
    page.getByText("Awaiting trained model", { exact: true }),
  ).toBeVisible();
  const sample = await page.request.get("/api/__test__/sample.png");
  await page.locator("input[type=file]").setInputFiles({
    name: "board.png",
    mimeType: "image/png",
    buffer: await sample.body(),
  });
  await expect(
    page.getByAltText("Selected circuit board to inspect"),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Analyze PCB", exact: true }),
  ).toBeDisabled();
  await page.reload();
  await expect(
    page.locator(".desktop-nav").getByRole("link", { name: "Your account" }),
  ).toBeVisible();
  await page
    .locator(".desktop-nav")
    .getByRole("link", { name: "Your account" })
    .click();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome to PCB Detect" }),
  ).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/pcb-detect-login.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);

});

test("admin directory, real counts and immediate account disabling", async ({
  page,
  playwright,
}) => {

  const email = `managed-${Date.now()}@example.com`;
  const visitor = await playwright.request.newContext({
    baseURL: "http://127.0.0.1:5175",
    extraHTTPHeaders: { "X-PCB-Request": "1", Origin: "http://127.0.0.1:5175" },
  });
  expect(
    (
      await visitor.post("/api/auth/register", {
        data: { name: "Managed Inspector", email, password },
      })
    ).status(),
  ).toBe(201);
  await signIn(page);
  await page
    .locator(".desktop-nav")
    .getByRole("link", { name: "Administration", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "The whole picture." }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: "Search users" }).fill(email);
  const row = page.getByRole("row").filter({ hasText: email });
  await row.getByRole("button", { name: "Manage", exact: true }).click();
  await page.getByLabel("Account enabled").uncheck();
  await page.getByRole("button", { name: "Save access settings" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(row.getByText("Disabled", { exact: true })).toBeVisible();
  expect((await visitor.get("/api/auth/me")).status()).toBe(401);
  await page.screenshot({
    path: "/private/tmp/pcb-detect-admin.png",
    fullPage: true,
  });
  await visitor.dispose();

});

test("fixture detection displays boxes, coordinates, guidance, exports and history", async ({
  page,
}) => {

  await signIn(page);
  const enabled = await page.request.post("/api/__test__/enable-inference", {
    headers: { "X-PCB-Request": "1", Origin: "http://127.0.0.1:5175" },
  });
  expect(enabled.status()).toBe(200);
  await page.goto("/analyze");
  await page.getByRole("tab", { name: "Image URL", exact: true }).click();
  await page
    .getByLabel("Direct image URL")
    .fill("http://127.0.0.1:5175/api/__test__/sample.png");
  await page.getByRole("button", { name: "Load image", exact: true }).click();
  await expect(
    page.getByAltText("Selected circuit board to inspect"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Analyze PCB", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(
    dialog.getByAltText("Circuit board with predicted defect bounding boxes"),
  ).toBeVisible();
  await expect(
    dialog.getByText("Box (pixels): [1, 1, 12, 12]", { exact: true }),
  ).toBeVisible();
  await expect(
    dialog.getByText("Critical review priority", { exact: true }),
  ).toBeVisible();
  await expect(dialog.getByText("88%", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/pcb-detect-result.png",
    fullPage: true,
  });
  await dialog
    .getByRole("button", { name: "Show original", exact: true })
    .click();
  await expect(dialog.getByAltText("Original circuit board")).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "Export JSON", exact: true })
    .click();
  expect((await downloadPromise).suggestedFilename()).toMatch(/\.json$/);
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await page
    .locator(".desktop-nav")
    .getByRole("link", { name: "History", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Inspection History", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "View sample.png", exact: true }),
  ).toBeVisible();
  await page
    .locator(".desktop-nav")
    .getByRole("link", { name: "Dashboard", exact: true })
    .click();
  await expect(page.getByText("Short", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "/private/tmp/pcb-detect-dashboard.png",
    fullPage: true,
  });

});

test("mobile navigation, protected deep links and account sign out", async ({
  page,
}) => {

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "/private/tmp/pcb-detect-mobile.png",
    fullPage: true,
  });
  await page.goto("/history");
  await expect(
    page.getByRole("heading", { name: "Welcome to PCB Detect" }),
  ).toBeVisible();
  await page.getByLabel("Email", { exact: true }).fill("admin@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign In", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Inspection History", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .locator(".mobile-nav")
    .getByRole("link", { name: "Your account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your account", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome to PCB Detect" }),
  ).toBeVisible();

});
