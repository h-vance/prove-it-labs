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
// Every page a visitor can land on, which is not the same as every directory
// with an index.html in it. Astro emits the not-found page as a bare 404.html,
// so it matched neither branch and thirty of the thirty-one built pages were
// checked. A 404 is a page people reach, and on this site it carries the site
// navigation and the search box like any other.
function findPages(dir = DIST, prefix = "") {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...findPages(full, `${prefix}/${entry}`));
    } else if (entry === "index.html") {
      found.push(prefix === "" ? "/" : `${prefix}/`);
    } else if (entry.endsWith(".html")) {
      found.push(`${prefix}/${entry}`);
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
const seenProofStates = new Set();
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

// The Content-Security-Policy is checked here rather than in a pass of its own,
// because this loop already visits every page in both themes and opens the
// hints, the solution, the quiz and the terminal. A policy that only holds on a
// page nobody touched is not worth having, and search and the quiz are exactly
// where a policy usually breaks.
//
// A policy is not proved by reading it out of the HTML. It is proved by a
// browser enforcing it and having nothing to complain about.
const CSP_COMPLAINT = /Content Security Policy|Refused to (load|execute|apply|connect)/i;
let visiting = "";
const cspFailures = [];

for (const theme of ["dark", "light"]) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    colorScheme: theme,
  });
  const page = await context.newPage();

  page.on("console", (message) => {
    if (CSP_COMPLAINT.test(message.text())) {
      cspFailures.push({ theme, path: visiting, detail: message.text() });
    }
  });

  for (const path of pages) {
    visiting = path;
    await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });

    const policies = await page.locator(
      'meta[http-equiv="Content-Security-Policy"]').count();
    if (policies !== 1) {
      cspFailures.push({
        theme,
        path,
        detail: `the page carries ${policies} policies, not one. `
          + `Did the build skip scripts/csp.mjs?`,
      });
    }
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

    // Hints and the solution, which this gate had never once looked at.
    //
    // They were islands that rendered nothing until clicked, so the page as
    // served contained none of their content, and this file had bespoke steps
    // to force the terminal and the quiz into their real states and no
    // equivalent for these two. That is the richest markup on the page, tables
    // and blockquotes and fenced code, and it went unscanned on every exercise
    // in both themes for as long as the gate existed. An audit found the
    // heading outline was broken in all twenty five as a result.
    //
    // Native disclosures now, rather than islands that rendered nothing until
    // clicked. Opened in order, because the enhancement script folds hint n+1
    // away until hint n has been opened, and a scan of a hidden element is a
    // scan of nothing.
    const revealed = [];
    const hints = page.locator("details[data-hint]");
    const hintCount = await hints.count();
    for (let index = 0; index < hintCount; index += 1) {
      await hints.nth(index).locator("summary").click();
    }
    if (hintCount > 0) {
      await page.waitForSelector("details[data-hint][open] .reveal__item");
      revealed.push("hints");
      seenRevealStates.add("hints");
    }

    const solution = page.locator("details[data-solution]");
    if (await solution.count()) {
      await solution.locator("summary").click();
      await page.waitForSelector("details[data-solution][open] .reveal__item");
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
      //
      // Toggled rather than clicked, because the button is a toggle and whether
      // it is already on is remembered per exercise rather than per page. The
      // home page carries docker/01's terminal, so it shares a storage key with
      // that exercise's own page: within one theme's context the first of the
      // two revealed the list, and the second dutifully clicked it shut again
      // and then waited thirty seconds for content it had just hidden.
      if (!(await page.locator(".terminal__list code").first().isVisible())) {
        await page.locator(".terminal .reveal__button--quiet").click();
      }
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

    // The proof record, in all three of its states.
    //
    // As served it is twenty five unanswered questions, which is the one state
    // with nothing to fail on. The refusal message and the proven item are both
    // rendered only after somebody pastes something, and the proven item is the
    // only place on the site where a color carries any part of a meaning, so
    // leaving it unscanned would leave the risk unmeasured.
    //
    // The exercise id comes off the page's own links rather than being written
    // here, so this cannot start passing against an exercise that was renamed.
    if (await page.locator(".proof__import").count()) {
      const field = page.locator("#proof-paste");
      const importButton = page.locator(".proof__import .reveal__button").first();

      await field.fill("this is not json");
      await importButton.click();
      await page.waitForSelector(".proof__message");
      seenProofStates.add("refused");

      // Refusing has to leave the record alone, which is the whole reason the
      // parse and the write are separate steps in the component.
      if (await page.locator(".proof__item--proven").count()) {
        failures.push({
          theme,
          path: `${path} (refused import)`,
          violations: [{
            id: "proof-record-refusal",
            help: "A refused import marked an exercise proven, so it wrote before it parsed.",
            nodes: [],
          }],
        });
      }

      const first = await page.locator(".proof__item .proof__link a").first().getAttribute("href");
      const id = first.replace(/^.*\/exercises\//, "");
      await field.fill(JSON.stringify({ completed: [id], total: 25, by_track: {} }));
      await importButton.click();
      await page.waitForSelector(".proof__item--proven");
      seenProofStates.add("imported");

      await page.evaluate(() =>
        Promise.all(document.getAnimations().map((animation) => animation.finished.catch(() => {}))),
      );
      const proofResult = await scan(page);
      checks += 1;
      if (proofResult.violations.length > 0) {
        failures.push({ theme, path: `${path} (imported)`, violations: proofResult.violations });
      }

      // Leave nothing behind for the next theme's pass, which shares no context
      // but would share an origin.
      await page.locator(".proof__import .reveal__button--quiet").click();
      await page.waitForSelector(".proof__item--proven", { state: "detached" });
      seenProofStates.add("cleared");
    }
  }
  await context.close();
}

// --------------------------------------------------------------------- 320px
//
// WCAG 2.2 AA, 1.4.10 Reflow: at 320 CSS pixels, which is a small phone and
// also what a 1280px window looks like at 400% zoom, content must not require
// scrolling in two directions. Nothing had ever looked at this site narrow,
// and it carries a monospace terminal and wide preformatted SQL tables, so it
// is a real risk rather than a formality.
//
// A wide block is allowed to scroll inside its own container. What is not
// allowed is the whole page scrolling sideways, which is what this measures.
// One theme: reflow is a layout property and does not change with color.
{
  const context = await browser.newContext({ viewport: { width: 320, height: 720 } });
  const page = await context.newPage();

  for (const path of pages) {
    await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });

    const overflow = await page.evaluate(() => {
      const root = document.documentElement;
      if (root.scrollWidth <= root.clientWidth + 1) return null;
      // Name the widest thing, or the failure is a number with nowhere to go.
      let worst = null;
      for (const node of document.querySelectorAll("body *")) {
        const box = node.getBoundingClientRect();
        if (box.right <= root.clientWidth + 1) continue;
        if (!worst || box.right > worst.right) {
          worst = {
            right: Math.round(box.right),
            tag: node.tagName.toLowerCase(),
            className: typeof node.className === "string" ? node.className : "",
          };
        }
      }
      return { page: root.scrollWidth, viewport: root.clientWidth, worst };
    });

    checks += 1;
    if (overflow) {
      const culprit = overflow.worst
        ? `${overflow.worst.tag}${overflow.worst.className ? `.${overflow.worst.className.split(" ").join(".")}` : ""} reaches ${overflow.worst.right}px`
        : "no single element could be blamed";
      failures.push({
        theme: "320px",
        path,
        violations: [{
          impact: "serious",
          id: "reflow",
          help: `the page scrolls sideways at 320px: ${overflow.page}px of content in ${overflow.viewport}px`,
          nodes: [{ target: [culprit] }],
        }],
      });
    }

    const narrow = await scan(page);
    checks += 1;
    if (narrow.violations.length > 0) {
      failures.push({ theme: "320px", path, violations: narrow.violations });
    }
  }
  await context.close();
}

// ------------------------------------------------------------- without script
//
// The reason the hints and the solution stopped being islands.
//
// They used to be props on a Preact component, so the markup shipped in every
// page escaped inside an attribute: bytes paid for on every visit, and not one
// word readable without JavaScript. Nothing here had ever loaded a page with
// scripting off, so nothing would have said so.
//
// `<details>` opens with no script at all, which is the whole point, and this
// is the check that keeps it true.
{
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    javaScriptEnabled: false,
  });
  const page = await context.newPage();
  const exercisePages = pages.filter((path) => path.startsWith("/exercises/"));

  for (const path of exercisePages) {
    await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "domcontentloaded" });

    // Every disclosure opened the way a person would, by clicking. If the
    // enhancement script were still required for any of this, these clicks
    // would do nothing and the assertions below would find empty pages.
    for (const summary of await page.locator("details.reveal__disclosure summary").all()) {
      await summary.click();
    }

    const readable = await page.evaluate(() => {
      const visible = (node) =>
        node && node.getClientRects().length > 0 && node.textContent.trim().length > 0;
      const hints = [...document.querySelectorAll("details[data-hint] .reveal__item")];
      const solution = document.querySelector("details[data-solution] .reveal__item");
      return {
        hints: hints.length,
        hintsVisible: hints.filter(visible).length,
        solutionVisible: visible(solution),
        solutionChars: solution ? solution.textContent.trim().length : 0,
      };
    });

    checks += 1;
    if (readable.hints === 0 || readable.hintsVisible !== readable.hints) {
      failures.push({
        theme: "no javascript",
        path,
        violations: [{
          impact: "critical",
          id: "content-needs-script",
          help: `${readable.hintsVisible} of ${readable.hints} hints are readable without JavaScript`,
          nodes: [{ target: ["details[data-hint] .reveal__item"] }],
        }],
      });
    }

    checks += 1;
    // A length, not just presence. An empty container that happens to be in
    // the page would satisfy "the element exists" and teach nobody anything.
    if (!readable.solutionVisible || readable.solutionChars < 200) {
      failures.push({
        theme: "no javascript",
        path,
        violations: [{
          impact: "critical",
          id: "content-needs-script",
          help: `the solution is not readable without JavaScript (${readable.solutionChars} characters visible)`,
          nodes: [{ target: ["details[data-solution] .reveal__item"] }],
        }],
      });
    }

    seenRevealStates.add("no-script");
  }

  // No axe here, deliberately. It injects itself into the page and runs there,
  // so with scripting off it cannot run at all; the first attempt at this died
  // on a garbage-collected promise rather than reporting anything. The markup
  // is identical either way now that it is server-rendered, and the scans
  // above cover it. What this pass uniquely proves is that the content is
  // readable, which is the thing that was broken.
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
  ["no-script", "a page with scripting turned off"],
]) {
  if (!seenRevealStates.has(state)) {
    console.error(`axe: ${described} was never revealed, so its markup went unchecked.`);
    process.exit(1);
  }
}

// And the proof record, whose three interesting states all need a paste to
// exist at all. A run that opened the page and did nothing would scan twenty
// five identical "Not started" rows and report the same clean line.
for (const [state, described] of [
  ["refused", "a refused import"],
  ["imported", "an imported record"],
  ["cleared", "the record being cleared again"],
]) {
  if (!seenProofStates.has(state)) {
    console.error(`axe: the proof record never showed ${described}, so that state went unchecked.`);
    process.exit(1);
  }
}

if (cspFailures.length > 0) {
  console.error(
    `csp: ${cspFailures.length} Content-Security-Policy problem(s). The policy ` +
      `is generated from the built pages by scripts/csp.mjs, so this means the ` +
      `page loads something the policy does not cover rather than a stale hash.\n`,
  );
  for (const failure of cspFailures.slice(0, 20)) {
    console.error(`  ${failure.theme.padEnd(5)} ${failure.path}`);
    console.error(`    ${failure.detail.slice(0, 200)}`);
  }
  process.exit(1);
}

if (failures.length === 0) {
  console.log(
    `axe: ${checks} checks across ${pages.length} pages in 2 themes, ` +
      `including both quiz verdicts, the terminal showing output and a refusal, ` +
      `every hint and solution opened, the proof record refusing and accepting ` +
      `an import, reflow at 320px, and every exercise read with JavaScript ` +
      `turned off. No violations.`,
  );
  console.log(
    `csp: enforced on all ${pages.length} pages in both themes with every ` +
      `disclosure, the quiz and the terminal exercised. Nothing refused.`,
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
