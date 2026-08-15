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
        ticketHtml: md(readIfPresent(join(dir, "ticket.md")) ?? ""),
        hintsHtml: hintFiles.map((name) => md(readFileSync(join(hintsDir, name), "utf8"))),
        solutionHtml: md(readIfPresent(join(dir, "solution.md")) ?? ""),
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
