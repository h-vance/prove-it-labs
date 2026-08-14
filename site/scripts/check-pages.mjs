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
    if (existsSync(join(REPO, "labs", track, slug, "meta.yaml"))) {
      expected.push({ id: `${track}/${slug}`, page: join(DIST, "exercises", track, slug, "index.html") });
    }
  }
}

if (expected.length === 0) {
  problems.push("No exercises were found in labs/. The loader would have nothing to build.");
}

for (const { id, page } of expected) {
  if (!existsSync(page)) {
    problems.push(`No page was built for ${id}`);
    continue;
  }
  const html = readFileSync(page, "utf8");
  // A page that renders but drops its content is as broken as a missing one.
  for (const [what, needle] of [
    ["the ticket", "CUSTOMER TICKET"],
    ["the scratchpad", "Investigation scratchpad"],
    ["the hints island", "reveal__button"],
    ["the start command", `tse start ${id}`],
  ]) {
    if (!html.includes(needle)) problems.push(`${id}: page is missing ${what}`);
  }
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

console.log(
  `Site content check passed: ${expected.length} exercise pages, all with ticket, scratchpad, and hints.`,
);
