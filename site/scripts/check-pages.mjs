#!/usr/bin/env node
/**
 * Asserts the built site actually contains a page for every exercise.
 *
 * This exists because of a real failure: the labs path was derived from
 * `import.meta.url`, which moves when Astro bundles, so every generated route
 * resolved to nothing. The build stayed green and simply produced four pages
 * instead of thirteen. A silent absence is the worst kind of regression, so it
 * gets its own check.
 */

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const SITE = resolve(import.meta.dirname, "..");
const REPO = resolve(SITE, "..");
const DIST = join(SITE, "dist");

/**
 * Weight budgets, both measured rather than guessed.
 *
 * Recorded output is embedded in the built HTML of every exercise page, so the
 * page grows with the transcript and nothing else would notice. When the
 * terminal landed the largest page went from 65,258 bytes to 71,144, which is
 * the cost of one transcript and is the number these budgets are set around.
 *
 * The cap is not tuned close. It exists to catch the structural regressions,
 * every transcript embedded on every page, or the per-entry line cap in
 * `tse record` being removed, rather than to argue about ordinary growth.
 *
 * Raw bytes, not compressed. The wire cost is smaller (that same page is 16KB
 * gzipped) but compression ratios move with content, and a budget that shifts
 * underneath you is a budget nobody trusts.
 */
const MAX_PAGE_BYTES = 90_000;

/**
 * Total JavaScript, which in a repository whose defining constraint is having
 * no dependencies is the number worth watching. Most of it is Starlight's own
 * ui-core at 94KB; everything this project wrote is around 16KB of it. A single
 * charting library would breach this.
 */
const MAX_SCRIPT_BYTES = 200_000;

if (!existsSync(DIST)) {
  console.error("dist/ not found. Run `npm run build` first.");
  process.exit(1);
}

const problems = [];

function directories(path) {
  if (!existsSync(path)) return [];
  return readdirSync(path)
    .filter((name) => !name.startsWith("_") && !name.startsWith("."))
    .filter((name) => statSync(join(path, name)).isDirectory());
}

const expected = [];
for (const track of directories(join(REPO, "labs"))) {
  for (const slug of directories(join(REPO, "labs", track))) {
    const dir = join(REPO, "labs", track, slug);
    if (existsSync(join(dir, "meta.yaml"))) {
      expected.push({
        id: `${track}/${slug}`,
        page: join(DIST, "exercises", track, slug, "index.html"),
        // A page with a transcript must actually carry the terminal. Reading
        // this from labs/ rather than trusting the page keeps the check
        // honest: the source of truth is the recording, not the build.
        recorded: existsSync(join(dir, "transcript.json")),
      });
    }
  }
}

if (expected.length === 0) {
  problems.push("No exercises were found in labs/. The loader would have nothing to build.");
}

let heaviest = { id: "", bytes: 0 };

for (const { id, page, recorded } of expected) {
  if (!existsSync(page)) {
    problems.push(`No page was built for ${id}`);
    continue;
  }
  const html = readFileSync(page, "utf8");
  // A page that renders but drops its content is as broken as a missing one.
  const needles = [
    ["the ticket", "CUSTOMER TICKET"],
    ["the scratchpad", "Investigation scratchpad"],
    ["the hints island", "reveal__button"],
    ["the start command", `tse start ${id}`],
  ];
  if (recorded) needles.push(["the lab terminal", "terminal__screen"]);

  for (const [what, needle] of needles) {
    if (!html.includes(needle)) problems.push(`${id}: page is missing ${what}`);
  }

  const bytes = Buffer.byteLength(html);
  if (bytes > heaviest.bytes) heaviest = { id, bytes };
  if (bytes > MAX_PAGE_BYTES) {
    problems.push(
      `${id}: the built page is ${bytes.toLocaleString()} bytes, over the ` +
        `${MAX_PAGE_BYTES.toLocaleString()} budget. Recorded output is embedded in ` +
        `every exercise page, so check the transcript before raising this.`,
    );
  }
}

const scripts = existsSync(join(DIST, "_astro"))
  ? readdirSync(join(DIST, "_astro")).filter((name) => name.endsWith(".js"))
  : [];
const scriptBytes = scripts.reduce(
  (total, name) => total + statSync(join(DIST, "_astro", name)).size,
  0,
);
if (scriptBytes > MAX_SCRIPT_BYTES) {
  problems.push(
    `Total JavaScript is ${scriptBytes.toLocaleString()} bytes across ${scripts.length} ` +
      `files, over the ${MAX_SCRIPT_BYTES.toLocaleString()} budget.`,
  );
}

for (const name of readdirSync(join(REPO, "reference")).filter((n) => n.endsWith(".md"))) {
  const slug = name.replace(/\.md$/, "");
  if (!existsSync(join(DIST, "reference", slug, "index.html"))) {
    problems.push(`No page was built for reference/${slug}`);
  }
}

for (const page of ["index.html", "how-it-works/index.html", "start/index.html"]) {
  if (!existsSync(join(DIST, page))) problems.push(`Missing core page: ${page}`);
}

if (problems.length > 0) {
  console.error("Site content check failed:\n");
  for (const problem of problems) console.error(`  ${problem}`);
  process.exit(1);
}

// Print the headroom rather than only the verdict, so it can be watched
// shrinking over several changes instead of noticed the day it fails.
const pageHeadroom = Math.round((1 - heaviest.bytes / MAX_PAGE_BYTES) * 100);
const scriptHeadroom = Math.round((1 - scriptBytes / MAX_SCRIPT_BYTES) * 100);

console.log(
  `Site content check passed: ${expected.length} exercise pages, all with ticket, scratchpad, and hints.\n` +
    `  Heaviest page: ${heaviest.id} at ${heaviest.bytes.toLocaleString()} bytes, ` +
    `${pageHeadroom}% under budget.\n` +
    `  JavaScript: ${scriptBytes.toLocaleString()} bytes across ${scripts.length} files, ` +
    `${scriptHeadroom}% under budget.`,
);
