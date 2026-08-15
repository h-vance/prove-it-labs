#!/usr/bin/env node
/**
 * Drives the lab terminal on the built site and asserts what it replays.
 *
 * The terminal has to collapse a typed command the same way tools/tse does, or
 * somebody types something reasonable and is told it was never recorded. Both
 * sides are asserted against tools/tests/fixtures/normalize.json: Python checks
 * its normalize_command directly, and this checks the shipped page, which is
 * the only thing that proves the TypeScript copy agrees rather than merely
 * having its own test suite.
 *
 * Every case is resolved against the real recordings rather than hard-coded, so
 * the fixture file stays about normalization and does not quietly become a list
 * of one exercise's commands.
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { chromium } from "playwright";

const SITE = resolve(import.meta.dirname, "..");
const REPO = resolve(SITE, "..");
const DIST = join(SITE, "dist");
const BASE = "/prove-it-labs";
const PORT = Number(process.env.TERMINAL_PORT ?? 4398);

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

const fixtures = JSON.parse(
  readFileSync(join(REPO, "tools", "tests", "fixtures", "normalize.json"), "utf8"),
);

/** Every recorded entry in the course, indexed by the keys it answers to. */
function recordings() {
  const byKey = new Map();
  const pages = [];
  for (const track of readdirSync(join(REPO, "labs"))) {
    const trackDir = join(REPO, "labs", track);
    if (!statSync(trackDir).isDirectory() || track.startsWith("_")) continue;
    for (const slug of readdirSync(trackDir)) {
      const file = join(trackDir, slug, "transcript.json");
      if (!existsSync(file)) continue;
      const path = `/exercises/${track}/${slug}/`;
      const { entries } = JSON.parse(readFileSync(file, "utf8"));
      pages.push({ path, entries });
      for (const entry of entries) {
        for (const key of entry.match) {
          if (!byKey.has(key)) byKey.set(key, { path, entry });
        }
      }
    }
  }
  if (pages.length === 0) {
    console.error("No transcripts found, so there is nothing to drive.");
    process.exit(1);
  }
  return { byKey, pages };
}

const { byKey, pages } = recordings();

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

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const failures = [];
let checks = 0;

function check(what, condition, detail = "") {
  checks += 1;
  if (!condition) failures.push(`${what}${detail ? `\n      ${detail}` : ""}`);
}

async function open(path) {
  await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".terminal__field");
}

/** Type into the real field and submit the way a learner would. */
async function run(text) {
  const field = page.locator(".terminal__field");
  await field.fill(text);
  await field.press("Enter");
  await page.waitForTimeout(20);
  return page.evaluate(() => {
    const entries = [...document.querySelectorAll(".terminal__entry")];
    const last = entries[entries.length - 1];
    return {
      count: entries.length,
      status: document.querySelector(".terminal__status")?.textContent ?? "",
      kind: !last
        ? "none"
        : last.querySelector(".terminal__output")
          ? "output"
          : last.querySelector(".terminal__refusal")
            ? "refusal"
            : "note",
      body: last?.querySelector(".terminal__output, .terminal__refusal, .terminal__note")
        ?.textContent ?? "",
    };
  });
}

// ------------------------------------------------------------ normalization

for (const fixture of fixtures) {
  const recorded = byKey.get(fixture.normalized);

  if (fixture.normalized === "") {
    // Whitespace is not a command. It must not add anything to the screen.
    await open(pages[0].path);
    const before = await page.locator(".terminal__entry").count();
    const after = await run(fixture.typed);
    check(
      `whitespace alone does nothing (${fixture.why})`,
      after.count === before,
      `the screen went from ${before} entries to ${after.count}`,
    );
    continue;
  }

  if (recorded) {
    await open(recorded.path);
    const result = await run(fixture.typed);
    check(
      `typed form reaches its recording (${fixture.why})`,
      result.kind === "output" && result.body === recorded.entry.output,
      result.kind === "output"
        ? "matched an entry, but not the one recorded for this command"
        : `got a ${result.kind} instead of the recorded output`,
    );
  } else {
    // No recording answers to this spelling, and that is the assertion: if the
    // page normalized more aggressively than tools/tse does, this would fold
    // onto a recorded command and quietly replay it.
    //
    // Which page matters. Run it somewhere the over-normalized form is not
    // recorded either and the assertion passes without testing anything, so
    // pick the page where folding case would actually find something. That is
    // the difference between this catching a lowercasing normalizer and not.
    const wouldFold = byKey.get(fixture.normalized.toLowerCase());
    await open(wouldFold ? wouldFold.path : pages[0].path);
    const result = await run(fixture.typed);
    check(
      `an unrecorded spelling stays unrecorded (${fixture.why})`,
      result.kind === "refusal",
      `got ${result.kind}, so the page normalized further than tools/tse does`,
    );
  }
}

// ----------------------------------------------------------------- refusals

const withRecording = pages[0];
await open(withRecording.path);

for (const [what, typed, expected] of [
  ["grading is refused", "tse check", /not by accident/i],
  ["the answer is refused", "tse answer", /not by accident/i],
  ["hints are refused", "tse hint", /not by accident/i],
  ["provisioning is refused", "tse start docker/01", /real containers/i],
  ["an unknown command is refused", "cat /etc/passwd", /nothing recorded for that/i],
]) {
  const result = await run(typed);
  check(what, result.kind === "refusal" && expected.test(result.body), result.body.slice(0, 90));
}

// A near miss says something close exists without naming it. Built from a real
// recorded command so it stays a near miss whatever the exercises become.
const nearMiss = `${withRecording.entries[0].match[0]} --definitely-not-recorded`;
const near = await run(nearMiss);
check(
  "a near miss says something close is recorded",
  near.kind === "refusal" && /something close is/i.test(near.body),
  near.body.slice(0, 90),
);
check(
  "a near miss does not name the command",
  !near.body.includes(withRecording.entries[0].match[0]),
  "the refusal quoted a recorded command back, which is a hint",
);

// ----------------------------------------------------------------- built-ins

const help = await run("help");
check("help explains itself", help.kind === "note" && /replay, not a shell/i.test(help.body));

await run(withRecording.entries[0].match[0]);
const clearedTo = await run("clear");
check("clear empties the screen", clearedTo.count === 0, `${clearedTo.count} entries remain`);

await run(withRecording.entries[0].match[0]);
const history = await page.evaluate(() =>
  Object.keys(localStorage).filter((key) => key.startsWith("proveit:terminal:")).length,
);
check("what was typed is remembered", history > 0);
await run("reset");
const afterReset = await page.evaluate(() => {
  const key = Object.keys(localStorage).find((name) => name.startsWith("proveit:terminal:"));
  return JSON.parse(localStorage.getItem(key) ?? "[]").length;
});
check("reset forgets what was typed", afterReset === 0, `${afterReset} commands remain`);

// ------------------------------------------------------------------ history

await open(withRecording.path);
const field = page.locator(".terminal__field");
await run("docker ps");
await run("kubectl get nodes");
await field.press("ArrowUp");
check("the up arrow recalls the last command", (await field.inputValue()) === "kubectl get nodes");
await field.press("ArrowUp");
check("the up arrow keeps walking back", (await field.inputValue()) === "docker ps");
await field.press("ArrowDown");
await field.press("ArrowDown");
check("the down arrow returns to an empty line", (await field.inputValue()) === "");

// --------------------------------------------------------------- the reveal

await open(withRecording.path);
// Counts the list items, not the container. The container is now always in the
// page and empty until asked, because the button carries `aria-controls`
// pointing at it and an attribute that points at nothing is worse than useless.
// What the learner must not see before asking is the commands themselves.
const listedBefore = await page.locator(".terminal__list li").count();
check("the recorded list is not shown until it is asked for", listedBefore === 0);
check(
  "the reveal button says whether it is open",
  (await page
    .getByRole("button", { name: /Show which commands are recorded/ })
    .getAttribute("aria-expanded")) === "false",
);
await page.getByRole("button", { name: /Show which commands are recorded/ }).click();
const listed = await page.locator(".terminal__list li").count();
check(
  "the reveal lists every recorded command",
  listed === withRecording.entries.length,
  `listed ${listed} of ${withRecording.entries.length}`,
);
const wrapped = await page.evaluate(() =>
  [...document.querySelectorAll(".terminal__list code")].some((node) =>
    node.textContent.includes("\\"),
  ),
);
check("the reveal lists commands in a form that can be typed back", !wrapped);

// ---------------------------------------------------------- nothing forbidden

for (const { path, entries } of pages) {
  for (const entry of entries) {
    check(
      `${path} records nothing that grades or answers`,
      !/\btse\s+(answer|hint|check|quiz)\b/.test(entry.command),
      entry.command,
    );
  }
}

await browser.close();
server.close();

if (failures.length === 0) {
  console.log(
    `Terminal check passed: ${checks} assertions across ${fixtures.length} normalization ` +
      `cases and ${pages.length} recorded exercises.`,
  );
  process.exit(0);
}

console.error(`Terminal check failed: ${failures.length} of ${checks} assertions.\n`);
for (const failure of failures) console.error(`  ${failure}`);
process.exit(1);
