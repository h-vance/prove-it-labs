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
const seenRevealStates = new Set();
let checks = 0;

/**
 * One scan, defined once, so every state is held to the same rules.
 *
 * heading-order and page-has-heading-one are named explicitly because axe tags
 * them best-practice rather than wcag, so a tag filter alone excludes them.
 * They are the rules that catch a fragment injected at the wrong level, which
 * is a real barrier for anybody navigating a long page by heading, and they are
 * exactly what this gate was missing when it had never opened a solution.
 */
const scan = (page) =>
  new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
    .withRules(["heading-order", "page-has-heading-one"])
    .analyze();

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

    const { violations } = await scan(page);

    checks += 1;
    if (violations.length > 0) {
      failures.push({ theme, path, violations });
    }

    // Hints and the solution, which this had never once looked at.
    //
    // Both islands render only their trigger until it is clicked, so the page
    // as served contains none of their content, and this file had bespoke steps
    // to force the terminal and the quiz into their real states and no
    // equivalent for these two. That is the richest markup on the page, tables
    // and blockquotes and fenced code, and it went unscanned on every exercise
    // in both themes for as long as the gate has existed. An audit found the
    // heading outline was broken in all twenty five as a result.
    // Scoped by section, not by button text. Matching `.reveal__button` on the
    // word "hint" also matched the terminal's own reveal, whose label ends "this
    // is close to a hint", so this clicked that instead, and the terminal step
    // further down then toggled it shut again and waited forever for a list
    // that was no longer there. Each island owns a section labelled by its own
    // heading, and that is unambiguous.
    const revealed = [];
    const hintButton = page.locator('section[aria-labelledby^="hints-"] .reveal__button').first();
    if (await hintButton.count()) {
      // Every hint, not just the first. They are separate articles and a later
      // one can carry markup the first does not.
      for (let click = 0; click < 6; click += 1) {
        if ((await hintButton.getAttribute("aria-disabled")) === "true") break;
        await hintButton.click();
      }
      revealed.push("hints");
      seenRevealStates.add("hints");
    }
    const solutionButton = page
      .locator('section[aria-labelledby^="solution-"] .reveal__button')
      .first();
    if (await solutionButton.count()) {
      await solutionButton.click();
      await page.waitForSelector('[id^="solution-body-"] > div');
      revealed.push("the solution");
      seenRevealStates.add("solution");
    }

    if (revealed.length > 0) {
      const opened = await scan(page);
      checks += 1;
      if (opened.violations.length > 0) {
        failures.push({
          theme,
          path: `${path} (${revealed.join(" and ")} open)`,
          violations: opened.violations,
        });
      }

      // The outline, asserted here rather than left to axe.
      //
      // Adding heading-order to the rule set above was supposed to cover this
      // and does not: axe only flags a level *increasing* by more than one, and
      // the bug this exists for is an injected h1 landing under an h2, which is
      // a decrease. Planting that exact defect against the extended axe run
      // produced no violation at all, which is why this is written out longhand.
      //
      // Two claims, both cheap: one top-level heading on the page, and no level
      // skipped on the way down.
      const outline = await page.evaluate(() =>
        [...document.querySelectorAll("h1, h2, h3, h4, h5, h6")]
          .filter((node) => node.offsetParent !== null || node.getClientRects().length > 0)
          .map((node) => ({ level: Number(node.tagName[1]), text: node.textContent.trim() })),
      );

      const tops = outline.filter((heading) => heading.level === 1);
      if (tops.length !== 1) {
        failures.push({
          theme,
          path: `${path} (${revealed.join(" and ")} open)`,
          violations: [{
            impact: "serious",
            id: "single-h1",
            help: `the page has ${tops.length} top-level headings once its content is open`,
            nodes: tops.map((heading) => ({ target: [`h1: ${heading.text.slice(0, 60)}`] })),
          }],
        });
      }

      for (let index = 1; index < outline.length; index += 1) {
        const previous = outline[index - 1];
        const current = outline[index];
        if (current.level - previous.level > 1) {
          failures.push({
            theme,
            path: `${path} (${revealed.join(" and ")} open)`,
            violations: [{
              impact: "moderate",
              id: "heading-skip",
              help: `h${previous.level} is followed by h${current.level}`,
              nodes: [{ target: [`h${current.level}: ${current.text.slice(0, 60)}`] }],
            }],
          });
          break;
        }
      }
      checks += 1;
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
      const result = await scan(page);

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

// And the same for the two islands this gate used to walk straight past. A run
// that opened neither would report the same clean line as one that opened both.
for (const [state, described] of [
  ["hints", "a hint"],
  ["solution", "a solution"],
]) {
  if (!seenRevealStates.has(state)) {
    console.error(`axe: ${described} was never revealed, so its markup went unchecked.`);
    process.exit(1);
  }
}

if (failures.length === 0) {
  console.log(
    `axe: ${checks} checks across ${pages.length} pages in 2 themes, ` +
      `including both quiz verdicts, the terminal showing output and a refusal, ` +
      `and every hint and solution opened, no violations.`,
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
