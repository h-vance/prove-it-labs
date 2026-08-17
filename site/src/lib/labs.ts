/**
 * Reads the exercises straight out of `labs/` at build time.
 *
 * The labs are the single source of truth. Nothing about an exercise is
 * duplicated into the site, so a page cannot drift from the thing it documents,
 * and adding an exercise needs no site change at all.
 */

import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseYaml } from "yaml";
import { marked } from "marked";

/**
 * Locate the repository by walking up for the directories that define it.
 *
 * Deriving this from `import.meta.url` breaks during a build: the module is
 * bundled and its URL no longer points at `src/lib/`, so the labs silently
 * resolve to nothing and every generated page disappears without an error.
 * Searching for a marker is stable under bundling and under being run from
 * either the repository root or the site directory.
 */
function findRepoRoot(): string {
  const candidates = [
    process.cwd(),
    resolve(process.cwd(), ".."),
    resolve(fileURLToPath(new URL("../../..", import.meta.url))),
  ];

  for (const start of candidates) {
    let current = start;
    for (let depth = 0; depth < 6; depth += 1) {
      if (existsSync(join(current, "labs")) && existsSync(join(current, "tools", "tse"))) {
        return current;
      }
      const parent = resolve(current, "..");
      if (parent === current) break;
      current = parent;
    }
  }

  throw new Error(
    "Could not locate the repository root: no directory containing both labs/ and tools/tse.",
  );
}

export const REPO_ROOT = findRepoRoot();
const LABS_DIR = join(REPO_ROOT, "labs");

/** Learner order, which is not the order the tracks were built in. */
export const TRACK_ORDER = [
  "linux",
  "docker",
  "networking",
  "kubernetes",
  "api",
  "sql",
  "observability",
  "communication",
  "mixed",
] as const;

export const TRACK_LABELS: Record<string, string> = {
  linux: "Linux and CLI",
  docker: "Docker",
  networking: "Networking, DNS, TLS",
  kubernetes: "Kubernetes",
  api: "APIs",
  sql: "SQL and PostgreSQL",
  observability: "Observability",
  communication: "Customer communication",
  mixed: "Mixed incidents",
};

/**
 * One word per permitted difficulty, indexed by the number itself.
 *
 * The permitted range lives in tools/tests/test_content.py, which asserts every
 * exercise declares a difficulty in 1 to 5. This list has to cover exactly that
 * range, and until now the only copy of it was an anonymous array literal
 * inside the exercise page template with nothing tying the two together. A
 * sixth permitted level would have rendered an empty difficulty on every page
 * that used it, silently, because indexing past the end of an array in
 * JavaScript is not an error.
 *
 * A test now reads this list and fails if it stops matching the range the
 * schema allows, in either direction.
 *
 * Index 0 is unused and deliberately unreachable: difficulty is one-based, and
 * padding the front is cheaper to read than subtracting one at every use.
 */
export const DIFFICULTY_LABELS = [
  "",
  "Gentle",
  "Straightforward",
  "Involved",
  "Hard",
  "Brutal",
] as const;

/** The word for a difficulty, or a loud failure at build time rather than a blank. */
export function difficultyLabel(difficulty: number): string {
  const label = DIFFICULTY_LABELS[difficulty];
  if (!label) {
    throw new Error(
      `Difficulty ${difficulty} has no label. Add one to DIFFICULTY_LABELS in ` +
        `src/lib/labs.ts, and widen the range in tools/tests/test_content.py to match.`,
    );
  }
  return label;
}

export interface QuizOption {
  text: string;
  /** Exactly one option per question carries this. test_content.py enforces it. */
  correct: boolean;
  /** Present on every option, right and wrong. "Correct" alone teaches nothing. */
  explanation: string;
}

export interface QuizQuestion {
  question: string;
  options: QuizOption[];
}

export interface TranscriptEntry {
  /** As written in commands.txt. Shown only when the list is deliberately revealed. */
  command: string;
  /**
   * The normalized spellings this entry answers to, written by `tse record`.
   *
   * The aliases from commands.txt are already folded in here, which is why they
   * are not carried separately onto the page: they would be bytes in every
   * built exercise page that nothing reads.
   */
  match: string[];
  output: string;
  exit: number;
}

export interface Exercise {
  id: string;
  track: string;
  trackLabel: string;
  slug: string;
  /** Site path, e.g. /exercises/docker/01-service-unavailable-after-deploy */
  href: string;
  title: string;
  proofQuestion: string;
  stack: string;
  tier: "core" | "stretch";
  difficulty: number;
  minutes: number;
  prerequisites: string[];
  commandsIntroduced: string[];
  evidenceLayers: string[];
  interviewRelevance: string;
  teaches: string;
  ticketHtml: string;
  hintsHtml: string[];
  solutionHtml: string;
  questions: QuizQuestion[];
  transcript: TranscriptEntry[];
}

marked.setOptions({ gfm: true, breaks: false });

/**
 * Shift a fragment's headings so its highest one lands at `topLevel`.
 *
 * Authored markdown opens at whatever level reads best on disk, which is h1 for
 * a solution and h2 for a ticket. Injected into a page it stops being a
 * document and becomes a fragment sitting under a heading that is already
 * there, and one that opens at the wrong level either repeats a level or skips
 * one. Both break the outline screen reader users navigate a long page by, and
 * a solution opening at h1 puts a second top-level heading halfway down.
 *
 * Every one of the twenty five solutions did exactly that, and the template
 * bakes it in for every future one. Nobody had noticed because the
 * accessibility scan had never opened a solution: the island renders nothing
 * until it is clicked, and the scan clicked the terminal and the quiz and not
 * this.
 *
 * Measured rather than assumed. A fixed "shift down by two" was the first fix
 * here and it was wrong for tickets, which already start at h2, so it produced
 * an h2 followed by an h4. Reading the fragment's own top level means an author
 * can open a file at any level and the page stays correct, which is one less
 * rule for somebody writing an exercise to know.
 */
function shiftHeadingsTo(html: string, topLevel: number): string {
  const levels = [...html.matchAll(/<h([1-6])[\s>]/g)].map((match) => Number(match[1]));
  if (levels.length === 0) return html;
  const shift = topLevel - Math.min(...levels);
  if (shift === 0) return html;
  return html.replace(
    /<(\/?)h([1-6])([\s>])/g,
    (_match, slash: string, level: string, after: string) =>
      `<${slash}h${Math.min(6, Math.max(1, Number(level) + shift))}${after}`,
  );
}

function md(source: string): string {
  const html = marked.parse(source, { async: false }) as string;
  // A block that scrolls has to be reachable from a keyboard, which is WCAG
  // 2.1.1 and is what axe's scrollable-region-focusable rule checks. Tickets in
  // the SQL track carry wide preformatted tables, and on a narrow screen those
  // scroll, so without this they are content nobody navigating by keyboard can
  // read. Starlight adds this to its own fenced blocks; markdown rendered here
  // never passes through that.
  return html.replace(/<pre>/g, '<pre tabindex="0">');
}

function readIfPresent(path: string): string | null {
  return existsSync(path) ? readFileSync(path, "utf8") : null;
}

function directories(path: string): string[] {
  if (!existsSync(path)) return [];
  return readdirSync(path)
    .filter((name) => !name.startsWith("_") && !name.startsWith("."))
    .filter((name) => statSync(join(path, name)).isDirectory())
    .sort();
}

/**
 * The exercise's question set.
 *
 * Deliberately throws rather than returning an empty list. A malformed file
 * would otherwise render a page with the quiz silently missing, and a build
 * that stays green while dropping content is the failure mode this project
 * already got caught by once.
 */
function readQuestions(dir: string): QuizQuestion[] {
  const source = readIfPresent(join(dir, "questions.json"));
  if (!source) return [];
  try {
    return JSON.parse(source) as QuizQuestion[];
  } catch (error) {
    throw new Error(`${join(dir, "questions.json")} is not valid JSON: ${String(error)}`);
  }
}

/**
 * The exercise's recorded output.
 *
 * Only the fields the page actually uses are carried through. Everything here
 * is embedded verbatim into the built HTML, so a field nobody reads is weight
 * on every visit, and site/scripts/check-pages.mjs holds that to a budget.
 *
 * Throws on malformed JSON for the same reason readQuestions does.
 */
function readTranscript(dir: string): TranscriptEntry[] {
  const source = readIfPresent(join(dir, "transcript.json"));
  if (!source) return [];
  try {
    const parsed = JSON.parse(source) as { entries?: TranscriptEntry[] };
    return (parsed.entries ?? []).map(({ command, match, output, exit }) => ({
      command,
      match,
      output,
      exit,
    }));
  } catch (error) {
    throw new Error(`${join(dir, "transcript.json")} is not valid JSON: ${String(error)}`);
  }
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

let cached: Exercise[] | null = null;

export function loadExercises(): Exercise[] {
  if (cached) return cached;

  const exercises: Exercise[] = [];

  for (const track of directories(LABS_DIR)) {
    for (const slug of directories(join(LABS_DIR, track))) {
      const dir = join(LABS_DIR, track, slug);
      const metaSource = readIfPresent(join(dir, "meta.yaml"));
      if (!metaSource) continue;

      const meta = parseYaml(metaSource) ?? {};
      const hintsDir = join(dir, "hints");
      const hintFiles = existsSync(hintsDir)
        ? readdirSync(hintsDir)
            .filter((name) => name.endsWith(".md"))
            .sort((a, b) => Number.parseInt(a, 10) - Number.parseInt(b, 10))
        : [];

      exercises.push({
        id: `${track}/${slug}`,
        track,
        trackLabel: TRACK_LABELS[track] ?? track,
        slug,
        href: `/exercises/${track}/${slug}`,
        title: meta.title ?? slug,
        proofQuestion: meta.proof_question ?? "",
        stack: meta.stack ?? "none",
        tier: meta.tier === "stretch" ? "stretch" : "core",
        difficulty: Number(meta.difficulty ?? 1),
        minutes: Number(meta.minutes ?? 0),
        prerequisites: asStringArray(meta.prerequisites),
        commandsIntroduced: asStringArray(meta.commands_introduced),
        evidenceLayers: asStringArray(meta.evidence_layers),
        interviewRelevance: meta.interview_relevance ?? "",
        teaches: meta.teaches ?? "",
        // Each target is one level below the heading the fragment is injected
        // under. The page renders `<h2>The ticket</h2>` and the solution island
        // renders its own h2, so both of those become h3. Each hint sits under
        // an h3 the component renders, so a hint starts at h4.
        ticketHtml: shiftHeadingsTo(md(readIfPresent(join(dir, "ticket.md")) ?? ""), 3),
        hintsHtml: hintFiles.map(
          (name) => shiftHeadingsTo(md(readFileSync(join(hintsDir, name), "utf8")), 4),
        ),
        solutionHtml: shiftHeadingsTo(md(readIfPresent(join(dir, "solution.md")) ?? ""), 3),
        questions: readQuestions(dir),
        transcript: readTranscript(dir),
      });
    }
  }

  const rank = (track: string) => {
    const index = TRACK_ORDER.indexOf(track as (typeof TRACK_ORDER)[number]);
    return index === -1 ? TRACK_ORDER.length : index;
  };

  exercises.sort((a, b) => rank(a.track) - rank(b.track) || a.id.localeCompare(b.id));
  cached = exercises;
  return exercises;
}

export function tracksWithExercises(): { track: string; label: string; exercises: Exercise[] }[] {
  const all = loadExercises();
  const seen: string[] = [];
  for (const exercise of all) {
    if (!seen.includes(exercise.track)) seen.push(exercise.track);
  }
  return seen.map((track) => ({
    track,
    label: TRACK_LABELS[track] ?? track,
    exercises: all.filter((exercise) => exercise.track === track),
  }));
}

export interface ReferenceDoc {
  slug: string;
  title: string;
  html: string;
}

/**
 * Reference material, also read from the repository rather than copied.
 *
 * These are the sheets a learner is told to print and keep beside them, so the
 * copy on the site and the copy in the repository must be the same file.
 */
export function loadReference(): ReferenceDoc[] {
  const dir = join(REPO_ROOT, "reference");
  if (!existsSync(dir)) return [];

  return readdirSync(dir)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .map((name) => {
      const source = readFileSync(join(dir, name), "utf8");
      const heading = source.match(/^#\s+(.+)$/m);
      return {
        slug: name.replace(/\.md$/, ""),
        title: heading?.[1]?.trim() || name,
        // Drop the H1: Starlight renders the title from frontmatter, and a
        // second one would put two top-level headings on the page.
        html: md(source.replace(/^#\s+.+$/m, "")),
      };
    });
}

/** Sidebar entries, generated so a new exercise never needs a config edit. */
export function sidebarFromLabs() {
  return tracksWithExercises().map(({ label, exercises }) => ({
    label,
    collapsed: false,
    items: exercises.map((exercise) => ({
      label: `${exercise.slug.split("-")[0]}. ${exercise.title}`,
      link: exercise.href,
      attrs: { "data-tier": exercise.tier },
    })),
  }));
}
