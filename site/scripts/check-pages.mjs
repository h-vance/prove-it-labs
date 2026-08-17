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
 *
 * Raised from 90,000 when the networking track landed at 85,679. That original
 * number was an estimate: it was set before any verbose track existed, from a
 * guess that a transcript costs about 5KB. Some do. `openssl s_client` prints
 * forty lines, which is what a support engineer actually runs first and so is
 * worth recording, and that page carries seven commands rather than five.
 *
 * Raising a budget because you hit it is how budgets stop meaning anything, so
 * the reasoning matters more than the number. The content was checked first and
 * is legitimate rather than bloat, the certificate body it used to carry is now
 * folded away at write time, and 100,000 still fails on anything that doubles a
 * page, which is the class of regression this exists to catch.
 */
const MAX_PAGE_BYTES = 100_000;

/**
 * Total JavaScript, which in a repository whose defining constraint is having
 * no dependencies is the number worth watching. Most of it is Starlight's own
 * ui-core at 94KB; everything this project wrote is around 16KB of it. A single
 * charting library would breach this.
 */
const MAX_SCRIPT_BYTES = 200_000;

/**
 * Stylesheets and fonts, which until the typeface landed nothing measured.
 *
 * The two budgets above cover HTML and JavaScript, and between them they gave
 * the comfortable impression that page weight was watched. It was not. A
 * webfont is the easiest kilobyte on a site to spend, it lands in neither of
 * those numbers, and a second face or a careless subset could have quietly
 * doubled what a first-time reader downloads with every gate still green.
 *
 * Measured at the point the font arrived: 157,486 bytes of CSS and no fonts at
 * all, going to 203,198 with IBM Plex Sans at 45,712. Two thirds of the CSS is
 * Pagefind's own search interface, which is vendored by the search integration
 * and is not ours to trim.
 *
 * 260,000 leaves room for the mono face this site should probably also ship,
 * and fails on a second full sans family, which is the regression worth
 * catching. Raw bytes, for the same reason as above.
 */
const MAX_STATIC_BYTES = 260_000;

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
      // The ticket's own heading, so this proves *this* exercise's ticket
      // rendered rather than that some fixed phrase appears somewhere. A
      // literal "CUSTOMER TICKET" needle failed the moment a communication
      // exercise arrived whose ticket is an internal note from a colleague,
      // which is the entire premise of that exercise.
      const ticket = join(dir, "ticket.md");
      const heading = existsSync(ticket)
        ? (readFileSync(ticket, "utf8").split("\n").find((line) => line.startsWith("#")) ?? "")
        : "";

      expected.push({
        id: `${track}/${slug}`,
        page: join(DIST, "exercises", track, slug, "index.html"),
        heading: heading.replace(/^#+\s*/, "").trim(),
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

/**
 * Compare ignoring entity escaping and whitespace, which markdown rewrites.
 *
 * Entities are removed before the non-alphanumeric strip rather than after.
 * `&#39;` survives that strip as the digits "39", so an apostrophe in a ticket
 * heading turned "morning's" into "morning39s" on one side and "mornings" on
 * the other, and every heading with an apostrophe failed.
 */
const squash = (text) =>
  text
    .replace(/&(?:#\d+|[a-z]+);/gi, "")
    .replace(/[^a-z0-9]+/gi, "")
    .toLowerCase();

for (const { id, page, recorded, heading } of expected) {
  if (!existsSync(page)) {
    problems.push(`No page was built for ${id}`);
    continue;
  }
  const html = readFileSync(page, "utf8");
  if (heading && !squash(html).includes(squash(heading))) {
    problems.push(`${id}: page is missing its ticket heading (${heading.slice(0, 50)})`);
  }
  // A page that renders but drops its content is as broken as a missing one.
  const needles = [
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

// Walked rather than read from one directory, because Pagefind writes its
// stylesheets outside _astro/ and a budget that missed two thirds of the CSS
// would be worse than none: it would report a number nobody would question.
function walkFor(directory, extensions) {
  const found = [];
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) found.push(...walkFor(path, extensions));
    else if (extensions.some((extension) => name.endsWith(extension))) found.push(path);
  }
  return found;
}

const staticAssets = walkFor(DIST, [".css", ".woff2", ".woff", ".ttf", ".otf"]);
const staticBytes = staticAssets.reduce((total, path) => total + statSync(path).size, 0);
const fonts = staticAssets.filter((path) => /\.(woff2?|[ot]tf)$/.test(path));
if (staticBytes > MAX_STATIC_BYTES) {
  problems.push(
    `Stylesheets and fonts are ${staticBytes.toLocaleString()} bytes across ` +
      `${staticAssets.length} files, over the ${MAX_STATIC_BYTES.toLocaleString()} ` +
      `budget. ${fonts.length} of them are fonts.`,
  );
}

// A face that is downloaded but never asked for is pure cost, and it is the
// exact residue of swapping one typeface for another and forgetting the old
// import. Checked by name against what the stylesheets actually reference.
const styleText = staticAssets
  .filter((path) => path.endsWith(".css"))
  .map((path) => readFileSync(path, "utf8"))
  .join("");
for (const font of fonts) {
  const name = font.slice(font.lastIndexOf("/") + 1);
  if (!styleText.includes(name)) {
    problems.push(`${name} ships but no stylesheet refers to it, so nothing will load it.`);
  }
}

for (const name of readdirSync(join(REPO, "reference")).filter((n) => n.endsWith(".md"))) {
  const slug = name.replace(/\.md$/, "");
  if (!existsSync(join(DIST, "reference", slug, "index.html"))) {
    problems.push(`No page was built for reference/${slug}`);
  }
}

for (const page of [
  "index.html",
  "how-it-works/index.html",
  "start/index.html",
  "proof/index.html",
]) {
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
const staticHeadroom = Math.round((1 - staticBytes / MAX_STATIC_BYTES) * 100);
const fontBytes = fonts.reduce((total, path) => total + statSync(path).size, 0);

console.log(
  `Site content check passed: ${expected.length} exercise pages, all with ticket, scratchpad, and hints.\n` +
    `  Heaviest page: ${heaviest.id} at ${heaviest.bytes.toLocaleString()} bytes, ` +
    `${pageHeadroom}% under budget.\n` +
    `  JavaScript: ${scriptBytes.toLocaleString()} bytes across ${scripts.length} files, ` +
    `${scriptHeadroom}% under budget.\n` +
    `  Styles and fonts: ${staticBytes.toLocaleString()} bytes across ` +
    `${staticAssets.length} files, ${staticHeadroom}% under budget. ` +
    `${fonts.length} font(s), ${fontBytes.toLocaleString()} bytes.`,
);
