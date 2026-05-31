import { chromium } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";
import os from "node:os";

const WEB_URL = process.env.CC_BRANCH_WEB_URL || "http://127.0.0.1:5173";
const API_URL = process.env.CC_BRANCH_API_URL || "http://127.0.0.1:5192";
const OUT_DIR = process.env.CC_BRANCH_SCREENSHOT_DIR || "/tmp/cc-branch-screenshot-qa";
const TEMP_PROJECT = path.join(os.tmpdir(), "cc-branch-onboarding-screenshot-project");

async function api(pathname, init) {
  const response = await fetch(`${API_URL}${pathname}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${pathname} failed: ${response.status} ${data.error || text}`);
  }
  return data;
}

async function screenshot(locator, fileName) {
  const filePath = path.join(OUT_DIR, fileName);
  await locator.screenshot({ path: filePath });
  return filePath;
}

async function fullPage(page, fileName) {
  const filePath = path.join(OUT_DIR, fileName);
  await page.screenshot({ path: filePath, fullPage: true });
  return filePath;
}

async function restoreProjects(originalProjects, tempProjectId) {
  if (tempProjectId) {
    try {
      await api("/api/projects/remove", {
        method: "POST",
        body: JSON.stringify({ id: tempProjectId }),
      });
    } catch {
      // Best effort cleanup; the QA result should still be reported.
    }
  }
  if (originalProjects?.active_project_id) {
    try {
      await api("/api/projects/activate", {
        method: "POST",
        body: JSON.stringify({ id: originalProjects.active_project_id }),
      });
    } catch {
      // Best effort restore.
    }
  }
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });
  await fs.mkdir(TEMP_PROJECT, { recursive: true });
  await fs.rm(path.join(TEMP_PROJECT, ".cc-branch"), { recursive: true, force: true });

  const originalProjects = await api("/api/projects");
  let tempProjectId = null;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1 });
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  const shots = [];
  const findings = [];

  try {
    await page.goto(WEB_URL, { waitUntil: "networkidle" });
    const nav = page.getByRole("navigation", { name: "Primary navigation" });
    await nav.waitFor({ state: "visible" });
    const navLabels = await nav.getByRole("tab").evaluateAll((nodes) =>
      nodes.map((node) => node.getAttribute("aria-label") || node.textContent?.trim())
    );
    if (!["Dashboard", "Workspace", "Project config", "Doctor"].every((label) => navLabels.includes(label))) {
      findings.push(`Primary nav labels missing or hidden: ${navLabels.join(", ")}`);
    }
    shots.push(await screenshot(nav, "01-primary-navigation-desktop.png"));

    const addButton = page.getByRole("button", { name: /add project/i }).first();
    await addButton.click();
    const dialog = page.getByRole("dialog", { name: /add project/i });
    await dialog.waitFor({ state: "visible" });
    await dialog.getByRole("button", { name: /ssh machine/i }).click();
    await dialog.getByText("Saved SSH targets").waitFor({ state: "visible" });
    shots.push(await screenshot(dialog, "02-add-project-ssh-targets.png"));
    const sshCards = await dialog.getByRole("button", { name: /use ssh target/i }).count();
    if (sshCards < 1) findings.push("SSH target cards were not visible.");
    await page.keyboard.press("Escape");

    const added = await api("/api/projects/add", {
      method: "POST",
      body: JSON.stringify({ path: TEMP_PROJECT, name: "Onboarding Screenshot QA" }),
    });
    tempProjectId = added.active_project_id;

    await page.reload({ waitUntil: "networkidle" });
    await page.getByRole("button", { name: /create workspace/i }).waitFor({ state: "visible" });
    shots.push(await fullPage(page, "03-onboarding-empty-project.png"));

    await page.getByRole("button", { name: /create workspace/i }).click();
    const wizard = page.getByRole("dialog", { name: /create workspace/i });
    await wizard.waitFor({ state: "visible" });
    await page.waitForFunction(() =>
      [...document.querySelectorAll("input")].some((input) => input.value === "frontend")
    );
    const paneNames = await wizard.locator("input").evaluateAll((nodes) => nodes.map((node) => node.value));
    if (!["frontend", "backend", "algorithm", "docs"].every((name) => paneNames.includes(name))) {
      findings.push(`Development wizard pane names not visible: ${paneNames.join(", ")}`);
    }
    const visibleAgents = await wizard.getByText(/codex|claude/i).count();
    if (visibleAgents < 4) findings.push(`Expected four visible agent selectors, found ${visibleAgents}.`);
    shots.push(await screenshot(wizard, "04-create-workspace-wizard-development.png"));

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(WEB_URL, { waitUntil: "networkidle" });
    await page.getByRole("navigation", { name: "Primary navigation" }).waitFor({ state: "visible" });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    if (overflow) findings.push("Mobile viewport has horizontal page overflow.");
    shots.push(await fullPage(page, "05-mobile-navigation-onboarding.png"));

    const summary = {
      webUrl: WEB_URL,
      apiUrl: API_URL,
      outputDirectory: OUT_DIR,
      screenshots: shots,
      consoleErrors,
      findings,
    };
    await fs.writeFile(path.join(OUT_DIR, "summary.json"), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await browser.close();
    await restoreProjects(originalProjects, tempProjectId);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
