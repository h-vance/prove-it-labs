// Put a Content-Security-Policy on every built page.
//
// GitHub Pages serves no custom headers, so the policy has to travel in the
// document as a <meta http-equiv>. That costs three directives which browsers
// ignore in meta form: frame-ancestors, report-uri and sandbox. They are left
// out rather than written and quietly dropped, because a policy that looks
// stricter than it is, is worse than an honest one.
//
// What this buys, precisely: the pages are static and already checked, so this
// is not what stops bad content getting into the build. That is the raw HTML
// gate in test_content.py. This is what protects a reader if something reaches
// the page after the build, which on a static site means a compromised host, a
// tampering proxy, or an extension. It blocks any script that is not one of
// the exact scripts built here, every third-party request, form posts anywhere,
// and object embedding.
//
// Hashes are computed from what was actually built rather than written down,
// so a Starlight upgrade that changes an inline script does not silently start
// failing. Per page, not pooled, so one page cannot vouch for another's script.

import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";

const DIST = new URL("../dist/", import.meta.url).pathname;
const MARKER = "<!--csp-->";

/** Every inline <script> and <style> body in one document. */
function inlineBodies(html, tag) {
  const bodies = [];
  const pattern = new RegExp(`<${tag}([^>]*)>([\\s\\S]*?)</${tag}>`, "g");
  for (const [, attributes, body] of html.matchAll(pattern)) {
    if (/\ssrc\s*=/.test(attributes)) continue;
    if (body.trim()) bodies.push(body);
  }
  return bodies;
}

function sha256(body) {
  return `'sha256-${createHash("sha256").update(body, "utf8").digest("base64")}'`;
}

function policyFor(html) {
  const scripts = [...new Set(inlineBodies(html, "script").map(sha256))];
  const styles = [...new Set(inlineBodies(html, "style").map(sha256))];
  return [
    // Nothing is allowed unless a directive below says so.
    "default-src 'none'",
    `script-src 'self' ${scripts.join(" ")}`.trim(),
    `style-src 'self' ${styles.join(" ")}`.trim(),
    // The syntax highlighter writes colors into style attributes, 2357 of them
    // across the site. Attribute styles cannot be hashed, and unlike scripts
    // they cannot call anything, so this is the one place the policy gives way.
    "style-src-attr 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    // The search index is fetched from this origin at runtime.
    "connect-src 'self'",
    "worker-src 'self'",
    "manifest-src 'self'",
    "form-action 'none'",
    "base-uri 'none'",
    "object-src 'none'",
  ].join("; ");
}

function walk(directory) {
  const out = [];
  for (const name of readdirSync(directory)) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) out.push(...walk(path));
    else if (name.endsWith(".html")) out.push(path);
  }
  return out;
}

const pages = walk(DIST);
if (pages.length === 0) {
  console.error("csp: no pages in dist/, so nothing was protected. Build first.");
  process.exit(1);
}

for (const page of pages) {
  const html = readFileSync(page, "utf8");
  if (!html.includes("<head>")) {
    console.error(`csp: ${page} has no <head> to put the policy in.`);
    process.exit(1);
  }
  const tag =
    `${MARKER}<meta http-equiv="Content-Security-Policy" ` +
    `content="${policyFor(html)}">`;
  writeFileSync(page, html.replace("<head>", `<head>${tag}`));
}

console.log(`csp: policy written into ${pages.length} page(s).`);
