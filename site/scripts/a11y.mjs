#!/usr/bin/env node
/**
 * Accessibility gate: every page, in both themes, against WCAG 2.2 AA.
 *
 * Runs against the built site rather than the dev server, so what is checked
 * is what would actually ship. Both themes are checked because contrast is the
 * failure that hides in the one you are not looking at.
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const DIST = resolve(import.meta.dirname, "..", "dist");
const BASE = "/prove-it-labs";
const PORT = Number(process.env.A11Y_PORT ?? 4399);

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".xml": "application/xml",
  ".wasm": "application/wasm",
};

if (!existsSync(DIST)) {
  console.error("dist/ not found. Run `npm run build` first.");
  process.exit(1);
}

/** Every built page, discovered rather than listed, so new ones cannot be missed. */
function findPages(dir = DIST, prefix = "") {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...findPages(full, `${prefix}/${entry}`));
    } else if (entry === "index.html") {
      found.push(prefix === "" ? "/" : `${prefix}/`);
    }
  }
  return found.sort();
}

const server = createServer(async (request, response) => {
  let path = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
  if (path.startsWith(BASE)) path = path.slice(BASE.length) || "/";
  if (path.endsWith("/")) path += "index.html";

  try {
    const body = await readFile(join(DIST, path));
    response.writeHead(200, { "Content-Type": MIME[extname(path)] ?? "application/octet-stream" });
    response.end(body);
  } catch {
    response.writeHead(404).end("not found");
  }
});

await new Promise((done) => server.listen(PORT, "127.0.0.1", done));

const pages = findPages();
const browser = await chromium.launch();
const failures = [];
const seenVerdicts = new Set();
const seenTerminalStates = new Set();
let checks = 0;

for (const theme of ["dark", "light"]) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    colorScheme: theme,
  });
  const page = await context.newPage();

  for (const path of pages) {
    await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });
    // Pin the theme explicitly: Starlight's own toggle writes this attribute,
    // and colorScheme alone would leave "auto" pages in the system default.
    await page.evaluate((value) => {
      document.documentElement.dataset.theme = value;
    }, theme);

    const { violations } = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
      .analyze();

    checks += 1;
    if (violations.length > 0) {
      failures.push({ theme, path, violations });
    }

    // Same reasoning as the quiz below: an empty terminal is the one state that
    // cannot fail. The scrollable output box, the refusal panel and the status
    // line only exist once something has been run, so they are put on screen
    // before the second scan. Both a replay and a refusal, because they are
    // styled differently and only one of them is a scrollable region.
    const hasTerminal = await page.locator(".terminal__field").count();
    if (hasTerminal) {
      // Open the reveal first. Its list gets scanned too, and it is where a
      // command known to be recorded on this page comes from, so nothing here
      // needs to know which exercise it is looking at.
      await page.locator(".terminal .reveal__button--quiet").click();
      await page.waitForSelector(".terminal__list code");

      // Real fill and keypress rather than a dispatched KeyboardEvent. A
      // synthetic event sent in the same tick as the input reaches the handler
      // before the component's state has flushed, so it submits an empty field
      // and nothing ever appears.
      const recorded = await page.locator(".terminal__list code").first().textContent();
      const field = page.locator(".terminal__field");
      for (const command of [recorded, "definitely not a recorded command"]) {
        await field.fill(command);
        await field.press("Enter");
      }

      // Counted rather than waited on. waitForSelector would throw on a state
      // that never rendered, and an uncaught timeout is a worse report than the
      // guard at the end of this file, which says which state went unchecked.
      await page.waitForSelector(".terminal__entry");
      for (const [state, selector] of [
        ["output", ".terminal__output"],
        ["refusal", ".terminal__refusal"],
      ]) {
        if (await page.locator(selector).count()) seenTerminalStates.add(state);
      }
    }

    // The quiz's verdict colors, its disabled options and its feedback panel
    // only exist once a question has been answered, so scanning the page as
    // served never sees them, and an unanswered quiz is the one state that
    // cannot fail a contrast check.
    //
    // Nothing here is told which option is correct, deliberately. Marking the
    // answer in the DOM so a test could find it would put it one inspector
    // click away from every learner. Picking a different position per question
    // produces both verdicts across the run instead, and the assertion at the
    // end proves it actually did.
    const questionCount = await page.evaluate(() => {
      const questions = [...document.querySelectorAll(".quiz__question")];
      questions.forEach((question, index) => {
        const options = [...question.querySelectorAll(".quiz__option")];
        options[index % options.length]?.click();
      });
      return questions.length;
    });

    if (questionCount > 0) {
      // Read the verdicts in a separate step. Reading them in the same tick as
      // the clicks returns an empty list, because the component has not
      // re-rendered yet, and the scan below would then silently examine an
      // untouched page.
      await page.waitForSelector(".quiz__feedback");
      // Let every running animation finish first. The feedback panel fades in,
      // and axe measuring mid-fade reads a blended, semi-transparent color: it
      // reported contrast as low as 1.77:1 for text that is fully compliant
      // once settled, with different values on every page. Waiting on the
      // animations rather than sleeping keeps it exact.
      await page.evaluate(() =>
        Promise.all(document.getAnimations().map((animation) => animation.finished.catch(() => {}))),
      );
      const verdicts = await page.evaluate(() =>
        [...document.querySelectorAll(".quiz__feedback")].map((node) =>
          node.classList.contains("quiz__feedback--correct") ? "correct" : "wrong",
        ),
      );
      for (const verdict of verdicts) seenVerdicts.add(verdict);
      const result = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
        .analyze();

      checks += 1;
      if (result.violations.length > 0) {
        failures.push({ theme, path: `${path} (answered)`, violations: result.violations });
      }
    }
  }
  await context.close();
}

await browser.close();
server.close();

// A gate that scans the answered quiz but never actually produced a wrong
// answer would pass while testing half of what it claims to test.
for (const verdict of ["correct", "wrong"]) {
  if (!seenVerdicts.has(verdict)) {
    console.error(
      `axe: no "${verdict}" quiz feedback was ever rendered, so its contrast went unchecked.`,
    );
    process.exit(1);
  }
}

// Same for the terminal. The scrollable output box and the refusal panel are
// the two states with anything to fail on, and neither exists until something
// has been run.
for (const [state, described] of [
  ["output", "replayed output"],
  ["refusal", "a refusal"],
]) {
  if (!seenTerminalStates.has(state)) {
    console.error(`axe: the terminal never rendered ${described}, so that state went unchecked.`);
    process.exit(1);
  }
}

if (failures.length === 0) {
  console.log(
    `axe: ${checks} checks across ${pages.length} pages in 2 themes, ` +
      `including both quiz verdicts and the terminal showing output and a refusal, ` +
      `no violations.`,
  );
  process.exit(0);
}

console.error(`axe: ${failures.length} page/theme combinations have violations.\n`);
for (const failure of failures) {
  console.error(`  ${failure.theme.padEnd(5)} ${failure.path}`);
  for (const violation of failure.violations) {
    console.error(`    [${violation.impact}] ${violation.id}: ${violation.help}`);
    for (const node of violation.nodes.slice(0, 3)) {
      console.error(`      ${node.target.join(" ")}`);
      if (node.failureSummary) {
        console.error(`      ${node.failureSummary.split("\n").join("\n      ")}`);
      }
    }
  }
  console.error("");
}
process.exit(1);
