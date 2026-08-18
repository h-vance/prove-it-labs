#!/usr/bin/env node
/**
 * Layout gate: the framework's prose spacing must not leak into our rows.
 *
 * Starlight gives stacked prose blocks their vertical rhythm with an
 * adjacent-sibling rule inside .sl-markdown-content, plus a smaller one between
 * list items. Neither is scoped to the top level, so both reach into every
 * component the page renders. In a column that is harmless. In a flex row or a
 * grid it is not spacing, it is a stagger: the first child stays put and every
 * later one drops.
 *
 * This exists because of a real failure. The facts bar on an exercise page sat
 * with Track 16 pixels above Time, Difficulty and Tier, and it read as a bug in
 * the bar. It was not. Three more containers had the same fault and nobody had
 * noticed, because the stagger is small enough to look like a design decision.
 *
 * Nothing else would catch it. The build is green, the types are clean, the
 * page weight is unchanged, and axe has no opinion about a row being crooked.
 * It takes a browser to see, because the margin comes from a stylesheet nobody
 * on this side wrote.
 *
 * The rule enforced: inside .sl-markdown-content, a child of a flex or grid
 * container has no margin-top, unless it is on the list below.
 */

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync, readdirSync, statSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { chromium } from "playwright";

const DIST = resolve(import.meta.dirname, "..", "dist");
const BASE = "/prove-it-labs";
const PORT = Number(process.env.LAYOUT_PORT ?? 4398);

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

/**
 * Margins in a row that are ours and are meant to be there.
 *
 * Kept as selector pairs rather than a blanket tolerance, so allowing one case
 * cannot quietly allow the next one. Adding to this list is a decision someone
 * has to write down.
 */
const DELIBERATE = [
  // The clip technique for visually hidden text is a 1px box with a -1px
  // margin. It is not laid out, so it cannot be staggered.
  { parent: "*", child: ".sr-only", why: "the visually-hidden clip box" },
  // The radio sits on the first line of its label rather than centered against
  // a label that may wrap to three lines.
  {
    parent: ".start__option",
    child: "input",
    why: "optical alignment of the radio with its first line",
  },
];

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
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const failures = [];
let containers = 0;

for (const path of pages) {
  await page.goto(`http://127.0.0.1:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });

  const found = await page.evaluate((deliberate) => {
    const ROW = new Set(["flex", "grid", "inline-flex", "inline-grid"]);
    const results = [];
    const rows = new Set();

    for (const child of document.querySelectorAll(".sl-markdown-content *")) {
      const parent = child.parentElement;
      if (!parent) continue;
      if (!ROW.has(getComputedStyle(parent).display)) continue;
      rows.add(parent);

      const margin = parseFloat(getComputedStyle(child).marginTop);
      if (!margin) continue;
      if (deliberate.some((rule) => parent.matches(rule.parent) && child.matches(rule.child))) {
        continue;
      }

      // How far this child sits below the first item in its row, which is the
      // number a reader would actually see. Reported alongside the margin
      // because a wrapped row can carry the margin without looking crooked,
      // and the person reading the failure needs to know which they have.
      const first = parent.firstElementChild;
      const drop =
        first && first !== child
          ? Math.round(child.getBoundingClientRect().top - first.getBoundingClientRect().top)
          : 0;

      const name = (element) =>
        element.tagName.toLowerCase() +
        (element.className && typeof element.className === "string"
          ? "." + element.className.trim().split(/\s+/).join(".")
          : "");

      results.push({ parent: name(parent), child: name(child), margin, drop });
    }

    return { results, rows: rows.size };
  }, DELIBERATE);

  containers += found.rows;

  for (const result of found.results) failures.push({ ...result, path });
}

await browser.close();
server.close();

if (failures.length > 0) {
  // One fault repeats on every page that renders the component, and several
  // times per page when the row has several items. Printed once per distinct
  // pair, or the real finding would be buried under three hundred lines of the
  // same sentence.
  const faults = new Map();
  for (const { parent, child, margin, drop, path } of failures) {
    const key = `${child} inside ${parent}`;
    const fault = faults.get(key) ?? { key, margin, worst: 0, count: 0, where: path };
    fault.count += 1;
    if (Math.abs(drop) > Math.abs(fault.worst)) fault.worst = drop;
    faults.set(key, fault);
  }

  console.error(`Layout check failed: ${faults.size} of them, in ${failures.length} places.\n`);
  for (const { key, margin, worst, count, where } of faults.values()) {
    console.error(
      `  ${key} carries margin-top: ${margin}px.\n` +
        `    ${count} place(s), first on ${where}, worst case ${worst}px below the ` +
        `first item in its row.\n` +
        `    That margin is the framework's prose spacing, not this stylesheet's.\n` +
        `    Take it back in custom.css, or add the pair to DELIBERATE here with a reason.\n`,
    );
  }
  process.exit(1);
}

console.log(
  `Layout check passed: ${containers} flex and grid containers across ${pages.length} pages, ` +
    `none carrying the framework's prose margin.`,
);
