// Build the animated terminal demo from the exercise's own recorded output.
//
// Why an SVG and not a GIF. A GIF of this is megabytes, needs ffmpeg or two
// more dependencies to produce, and is a bitmap that goes soft the moment
// anybody views it at a size other than the one it was rendered at. This is
// about 20KB of text, stays sharp at any size, diffs in review like code, and
// needs nothing installed. CSS animation inside an SVG served as an image is
// well supported; scripting is not, and none is used here.
//
// Why it is generated. The output below is not written by hand, and could not
// be: it is read from the same `transcript.json` the site's terminal replays
// and CI re-verifies against a freshly provisioned stack on every push. A
// hand-drawn demo is a claim about the product that nothing checks, which is
// the exact failure this whole repository is built to refuse. A test asserts
// the committed SVG still carries the recorded output, so a re-recording that
// changes what the system says fails the build rather than leaving a confident
// animation showing something that stopped being true.

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";

const REPO = resolve(import.meta.dirname, "..", "..");
const EXERCISE = join(REPO, "labs", "docker", "01-service-unavailable-after-deploy");
const OUT = join(REPO, "docs", "demo.svg");

/**
 * The two commands this demo shows, named exactly rather than by position.
 *
 * Indexing into the transcript would silently draw a different command the
 * first time somebody records a new one, and the demo would still look
 * perfectly convincing. Matching on the text means a rename fails loudly here
 * instead.
 */
const WANTED = [
  'docker ps -a --filter "label=com.docker.compose.project=proveit-docker"',
  "docker inspect --format '{{.State.Health.Status}}' proveit-docker-postgres-1",
];

const raw = JSON.parse(readFileSync(join(EXERCISE, "transcript.json"), "utf8"));
const entries = Array.isArray(raw) ? raw : (raw.entries ?? []);

const picked = WANTED.map((command) => {
  const entry = entries.find((candidate) => candidate.command === command);
  if (!entry) {
    console.error(
      `demo: no recording of\n  ${command}\nin ${EXERCISE}/transcript.json.\n` +
        `The demo is generated from real output, so it cannot draw a command ` +
        `nobody ran. Re-record, or pick a command that exists.`,
    );
    process.exit(1);
  }
  return entry;
});

// ------------------------------------------------------------------ layout

const FONT = 13;
const LINE = 20;
const PAD = 22;
const TOP = 52;
// Monospace advance width is about 0.6em across every face this could land in.
// The typing mask and the width below both depend on it, and being a little
// out moves a wipe by a few pixels or leaves a little slack on the right.
const CH = FONT * 0.6;
// Enough for the widest recorded line rather than a round number. `docker ps`
// prints a seven column table and the STATUS column is the whole point of
// showing it, so a width that cut it off would be showing the wrong half.
const MAX_CHARS = 150;

const escape = (text) =>
  text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

const fits = (text) =>
  text.length > MAX_CHARS ? `${text.slice(0, MAX_CHARS - 3)}...` : text;

const rows = [];
for (const [index, entry] of picked.entries()) {
  rows.push({ kind: "command", text: fits(entry.command) });
  const lines = entry.output.split("\n").filter((line) => line.trim().length > 0);
  // The first command prints a header and two containers, and both containers
  // are the point: one restarting, one healthy. The second prints one word.
  for (const line of lines.slice(0, 4)) rows.push({ kind: "output", text: fits(line) });
  if (index < picked.length - 1) rows.push({ kind: "gap", text: "" });
}
// An empty prompt at the end, because the demo is an invitation rather than a
// conclusion, and because a terminal with no cursor is a screenshot.
rows.push({ kind: "prompt", text: "" });

const CAPTION = [
  "The database is healthy. The customer still cannot load anything.",
  "Saying what that proves, and what it does not, is the exercise.",
];

const longest = Math.max(
  ...rows.map((row) => row.text.length + (row.kind === "command" ? 2 : 0)),
  ...CAPTION.map((line) => line.length),
);
const WIDTH = Math.round(PAD * 2 + longest * CH) + 10;

// ------------------------------------------------------------------ timing

const TYPE_PER_CH = 0.022;
const AFTER_COMMAND = 0.45;
const PER_OUTPUT = 0.14;
const HOLD = 3.4;

let clock = 0.5;
for (const row of rows) {
  row.at = clock;
  if (row.kind === "command") {
    row.typedFor = Math.min(1.6, row.text.length * TYPE_PER_CH);
    clock += row.typedFor + AFTER_COMMAND;
  } else if (row.kind === "gap") {
    clock += 0.25;
  } else if (row.kind === "prompt") {
    clock += 0.2;
  } else {
    clock += PER_OUTPUT;
  }
}
const CAPTION_AT = clock + 0.35;
const TOTAL = CAPTION_AT + HOLD;
const RULE_Y = TOP + rows.length * LINE + 6;
const CAPTION_TOP = RULE_Y + 26;
const HEIGHT = CAPTION_TOP + (CAPTION.length - 1) * LINE + PAD;
const pct = (seconds) => ((seconds / TOTAL) * 100).toFixed(3);

// ------------------------------------------------------------------- paint
//
// Colors are the site's own dark theme and its teal accent, so the demo and
// the page a reader lands on are recognizably the same product.

const BG = "#16181d";
const PANEL = "#1c1f26";
const RULE = "#2c313b";
const TEXT = "#d7dbe3";
const DIM = "#9aa3b2";
const ACCENT = "#93d8e2";
const WARN = "#f0b429";
const OK = "#4ade80";

const css = [];
const body = [];

css.push(`
  text { font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
         font-size: ${FONT}px; white-space: pre; }
  .dim { fill: ${DIM}; }
  .out { fill: ${TEXT}; }
  .cmd { fill: ${ACCENT}; }
  .note { fill: ${TEXT}; font-weight: 600; }
  .note2 { fill: ${DIM}; }
  .hl-warn { fill: ${WARN}; }
  .hl-ok { fill: ${OK}; }
`);



rows.forEach((row, index) => {
  const y = TOP + index * LINE;
  const id = `r${index}`;
  if (row.kind === "gap") return;

  if (row.kind === "prompt") {

    // The cursor lives inside this group rather than beside it. Its blink and
    // the group's reveal both animate opacity, so as siblings the later rule
    // wins and the cursor blinks away on an empty panel before the prompt it
    // belongs to has appeared. Nested, the two opacities multiply and it
    // arrives with its own line.
    css.push(`
      #${id} { animation: ${id}-in ${TOTAL}s infinite; }
      @keyframes ${id}-in {
        0%, ${pct(row.at - 0.01)}% { opacity: 0; }
        ${pct(row.at)}%, 96% { opacity: 1; }
        100% { opacity: 0; }
      }`);
    body.push(`  <g id="${id}">`);
    body.push(`    <text x="${PAD}" y="${y}" class="dim">$ </text>`);
    body.push(
      `    <rect id="cursor" x="${PAD + 2 * CH}" y="${y - FONT + 2}" width="${CH}" height="${FONT}"/>`,
    );
    body.push(`  </g>`);
    return;
  }

  if (row.kind === "command") {
    // Typed, by wiping a mask across the line rather than by emitting a frame
    // per character. One element, one animation, and it stays sharp.
    //
    // The wipe runs the full width of the panel rather than to a computed end
    // of the text. Sizing it to the string clipped both commands, because the
    // real advance width of a monospace face is not exactly 0.6em and is not
    // the same face for every reader: this SVG names a font stack and gets
    // whichever entry the viewer has. A wipe that runs past the end of a line
    // reveals empty space nobody can see. One that stops short cuts a command
    // in half permanently, which is what it did.
    const width = WIDTH - PAD * 2;
    css.push(`
      #${id}-clip rect { animation: ${id}-type ${TOTAL}s steps(${Math.max(
        4,
        Math.round(row.text.length / 2),
      )}) infinite; }
      @keyframes ${id}-type {
        0%, ${pct(row.at)}% { width: 0px; }
        ${pct(row.at + row.typedFor)}%, 96% { width: ${width}px; }
        100% { width: 0px; }
      }`);
    body.push(`  <clipPath id="${id}-clip"><rect x="${PAD}" y="${y - FONT}" width="0" height="${LINE}"/></clipPath>`);
    body.push(
      `  <g clip-path="url(#${id}-clip)"><text x="${PAD}" y="${y}"><tspan class="dim">$ </tspan><tspan class="cmd">${escape(
        row.text,
      )}</tspan></text></g>`,
    );
    return;
  }

  // The two words the whole demo exists to put next to each other.
  const markup = escape(row.text)
    .replace(/(Restarting \(\d+\))/, `</tspan><tspan class="hl-warn">$1</tspan><tspan class="out">`)
    .replace(/\b(healthy)\b/g, `</tspan><tspan class="hl-ok">$1</tspan><tspan class="out">`);

  css.push(`
    #${id} { animation: ${id}-in ${TOTAL}s infinite; }
    @keyframes ${id}-in {
      0%, ${pct(row.at - 0.01)}% { opacity: 0; }
      ${pct(row.at)}%, 96% { opacity: 1; }
      100% { opacity: 0; }
    }`);
  body.push(
    `  <text id="${id}" x="${PAD}" y="${y}" class="out"><tspan class="out">${markup}</tspan></text>`,
  );
});

// The caption sits below a hairline, outside the terminal's own flow, because
// it is the course talking rather than the machine. Conflating the two would
// be the one thing the terminal on the site refuses to do.
css.push(`
  #caption { animation: caption-in ${TOTAL}s infinite; }
  @keyframes caption-in {
    0%, ${pct(CAPTION_AT - 0.01)}% { opacity: 0; }
    ${pct(CAPTION_AT)}%, 96% { opacity: 1; }
    100% { opacity: 0; }
  }`);
body.push(`  <g id="caption">`);
body.push(
  `    <line x1="${PAD}" y1="${RULE_Y}" x2="${WIDTH - PAD}" y2="${RULE_Y}" stroke="${RULE}"/>`,
);
CAPTION.forEach((line, index) => {
  body.push(
    `    <text x="${PAD}" y="${CAPTION_TOP + index * LINE}" class="${
      index === 0 ? "note" : "note2"
    }">${escape(line)}</text>`,
  );
});
body.push(`  </g>`);

// A cursor, because a terminal without one looks like a screenshot.
css.push(`
  #cursor { animation: blink 1.06s steps(2, jump-none) infinite; fill: ${ACCENT}; }
  @keyframes blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }`);

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${HEIGHT}" viewBox="0 0 ${WIDTH} ${HEIGHT}" role="img" aria-label="A terminal replaying real recorded output from the Prove It course. Docker reports one container restarting and the postgres container healthy, and the caption reads: the database is healthy, the customer still cannot load anything.">
  <title>Prove It: the database is healthy and the customer still cannot load anything</title>
  <style>${css.join("\n")}</style>
  <rect width="${WIDTH}" height="${HEIGHT}" rx="10" fill="${BG}"/>
  <rect x="0.5" y="0.5" width="${WIDTH - 1}" height="${HEIGHT - 1}" rx="10" fill="none" stroke="${RULE}"/>
  <rect x="1" y="1" width="${WIDTH - 2}" height="34" rx="10" fill="${PANEL}"/>
  <rect x="1" y="26" width="${WIDTH - 2}" height="9" fill="${PANEL}"/>
  <line x1="1" y1="35" x2="${WIDTH - 1}" y2="35" stroke="${RULE}"/>
  <text x="${PAD}" y="23" class="dim">prove-it-labs</text>
  <text x="${WIDTH - PAD}" y="23" class="dim" text-anchor="end">docker/01 &#183; the ticket says "dashboard unavailable"</text>
${body.join("\n")}
</svg>
`;

writeFileSync(OUT, svg);
console.log(
  `demo: wrote docs/demo.svg, ${(svg.length / 1024).toFixed(1)}KB, ` +
    `${rows.filter((r) => r.kind !== "gap").length} lines over ${TOTAL.toFixed(1)}s, ` +
    `from ${picked.length} recorded commands.`,
);
if (!existsSync(OUT)) process.exit(1);
