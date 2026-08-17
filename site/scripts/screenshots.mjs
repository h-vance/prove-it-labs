#!/usr/bin/env node
/**
 * Regenerate the screenshots the README uses.
 *
 * Scripted rather than captured by hand, for the same reason the recordings in
 * `labs/` are: a picture of a user interface is a claim about it, and a claim
 * nothing can reproduce goes stale silently. Anyone can run this and get the
 * same images, and when the design changes the diff shows up in review as a
 * changed file rather than as a README quietly describing last month's site.
 *
 * Runs against the built site, not the dev server, so what is pictured is what
 * would actually ship. Same static server and base path as `a11y.mjs`.
 *
 *   npm run build && npm run screenshots
 */

import { createServer } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import { chromium } from "playwright";

const DIST = resolve(import.meta.dirname, "..", "dist");
const OUT = resolve(import.meta.dirname, "..", "..", "docs", "screenshots");
const BASE = "/prove-it-labs";
const PORT = Number(process.env.SHOT_PORT ?? 4398);

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

// Dark only. The site supports both and the accessibility gate checks both;
// these are illustrations rather than coverage, and one theme per shot keeps
// the README from turning into a gallery.
const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,
  colorScheme: "dark",
  reducedMotion: "reduce",
});

const EXERCISE = "/exercises/docker/01-service-unavailable-after-deploy/";

/**
 * What each image is for.
 *
 * Anchored on heading text rather than on an id or a pixel offset. The ids are
 * slug-prefixed, so the terminal's is `#terminal-docker/01-service-...`, which
 * is both unreadable here and fragile: renaming an exercise would silently
 * photograph the wrong part of the page rather than fail. The visible words
 * are the stable thing, and if they change, this stops rather than lying.
 */
const SHOTS = [
  {
    file: "home.png",
    path: "/",
    describe: "the landing page",
    viewport: true,
  },
  {
    file: "ticket.png",
    path: EXERCISE,
    describe: "the ticket: a symptom in the customer's words, naming no layer",
    element: ".ticket, blockquote",
  },
  {
    file: "terminal.png",
    path: EXERCISE,
    describe: "the replay terminal, after running one real command",
    element: "section.terminal",
    // Drive it before photographing it. An idle terminal shows a prompt and
    // proves nothing; the point of this component is that it replays output
    // captured from the broken system, so the image should show it doing that.
    type: "docker inspect --format '{{.State.Health.Status}}' proveit-docker-postgres-1",
  },
  {
    file: "quiz.png",
    path: EXERCISE,
    describe: "the questions, graded on what the evidence proved",
    element: "section.quiz, [class*=quiz]",
  },
];

await mkdir(OUT, { recursive: true });
const written = [];

for (const shot of SHOTS) {
  const page = await context.newPage();
  await page.goto(`http://127.0.0.1:${PORT}${BASE}${shot.path}`, { waitUntil: "networkidle" });

  if (shot.viewport) {
    await page.screenshot({ path: join(OUT, shot.file) });
    written.push(shot);
    await page.close();
    continue;
  }

  // Photograph the component rather than a slice of the page. Clipping to
  // pixel offsets meant hiding Starlight's sidebar to recover the width, which
  // left the content sitting off-center against an empty gutter, and it framed
  // the terminal's heading while cutting off the terminal. An element knows its
  // own bounds.
  const target = page.locator(shot.element).first();
  if ((await target.count()) === 0) {
    console.error(`  nothing matched ${shot.element} on ${shot.path}, for ${shot.file}`);
    process.exitCode = 1;
    await page.close();
    continue;
  }

  if (shot.type) {
    const field = page.locator("textarea.terminal__field").first();
    await field.fill(shot.type);
    await field.press("Enter");
    // The component types its reply out rather than pasting it, so wait for it
    // to stop rather than for a fixed interval.
    await page.waitForFunction(
      () => {
        const screen = document.querySelector(".terminal__screen");
        return screen && !screen.querySelector(".terminal__idle") && screen.textContent.trim().length > 0;
      },
      { timeout: 15000 },
    );
    await page.waitForTimeout(1200);
  }

  // An element screenshot crops to the element's own box, and a section whose
  // children sit flush against it comes out with the text touching the left
  // edge. Framing only: this pads the crop, it does not restyle the site.
  await target.evaluate((node) => {
    node.style.padding = "28px";
    node.style.boxSizing = "border-box";
  });

  // An element taller than the viewport is photographed by scrolling and
  // stitching the slices together, and anything the browser pins in place is
  // painted into every slice. Starlight's search box came out smeared across
  // the middle of the quiz, covering an answer, and that image had been in the
  // README since the screenshots first landed.
  //
  // Hidden rather than removed, so nothing underneath reflows and the image
  // still frames what a reader would see. Ancestors are skipped, or hiding the
  // chrome would hide the subject with it. The page is closed after each shot,
  // so none of this needs putting back.
  await target.evaluate((self) => {
    for (const node of document.querySelectorAll("body *")) {
      if (node.contains(self)) continue;
      const { position } = getComputedStyle(node);
      if (position === "fixed" || position === "sticky") node.style.visibility = "hidden";
    }
  });

  await target.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await target.screenshot({ path: join(OUT, shot.file) });
  written.push(shot);
  await page.close();
}

await browser.close();
server.close();

for (const shot of written) {
  console.log(`  wrote docs/screenshots/${shot.file}  ${shot.describe}`);
}
console.log(`\n${written.length} screenshot(s). They are committed, so review the diff.`);
