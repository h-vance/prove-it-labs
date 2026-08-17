import { useEffect, useState } from "preact/hooks";

export interface ProofEntry {
  id: string;
  trackLabel: string;
  title: string;
  href: string;
  proofQuestion: string;
  questionCount: number;
  hintCount: number;
}

interface Props {
  base: string;
  entries: ProofEntry[];
}

/**
 * What you have done here, and the one thing only the grader can tell us.
 *
 * Twenty five exercises, six families of stored state, and until this page
 * nothing ever read any of it back. Every component wrote its own key and
 * forgot about it, so somebody returning after a week had a record of their own
 * work sitting in their own browser that nothing would ever show them.
 *
 * The rules this page holds, written down because each was decided against
 * something more obvious:
 *
 *  - No points, no streaks, no badges, no levels, no confetti. Nothing here
 *    celebrates. It records. This whole course is built on showing the evidence
 *    and letting somebody else draw the conclusion, and a page handing out gold
 *    stars for opening a hint would contradict every other page in it.
 *  - A number appears only where it counts something real.
 *  - Nothing that happened on this site is proof. Nothing typed into a page
 *    fixes a system, so no amount of reading, answering or replaying can turn a
 *    question into a statement. Only `tse check` knows, which is the whole
 *    reason the import below exists.
 *  - State never rests on color. Proven and started differ in their words.
 *  - It says plainly what it cannot know.
 *
 * The answer key is deliberately not on this page. The quiz stores which option
 * was picked, so scoring here would mean shipping the correct index for all
 * seventy five questions into the HTML of a page anybody can read the source
 * of. `Quiz.tsx` stores its own score instead, which reveals nothing new about
 * a learner because it was already derivable from what sits beside it, and it
 * is the one form this page can read without being handed the answers.
 */

const KEY_COMPLETED = "proveit:completed";

/**
 * "Can I prove the route still exists?" -> "You can prove the route still exists."
 *
 * Every proof question is written as a question the learner asks themselves,
 * and a test holds them to the "Can I ..." opening precisely so this transform
 * cannot be handed something it would mangle into nonsense.
 */
function asStatement(question: string): string {
  return `You can ${question.replace(/^Can I\s+/, "").replace(/\?\s*$/, "")}.`;
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    /* Private mode, disabled storage, or JSON somebody edited by hand. */
    return fallback;
  }
}

interface Activity {
  answered: number;
  score: number | null;
  hintsRead: number;
  solutionRead: boolean;
  notesWritten: number;
  commandsRun: number;
}

const SCRATCHPAD_STEPS = 7;

function readActivity(id: string): Activity {
  const quiz = readJson<number[]>(`proveit:quiz:${id}`, []);
  const notes = readJson<Record<string, string>>(`proveit:scratchpad:${id}`, {});
  const terminal = readJson<string[]>(`proveit:terminal:${id}`, []);
  // Stored one-based by the hint script: 1 means the first hint is available
  // and none have been opened. Reading it as a count without that offset
  // credits every reader with a hint they never looked at.
  const unlocked = Number(localStorage.getItem(`proveit:hints:${id}`) ?? 1);

  return {
    answered: Array.isArray(quiz) ? quiz.filter((pick) => pick !== -1).length : 0,
    score: readJson<number | null>(`proveit:quiz-score:${id}`, null),
    hintsRead: Math.max(0, (Number.isFinite(unlocked) ? unlocked : 1) - 1),
    solutionRead: localStorage.getItem(`proveit:solution:${id}`) === "true",
    notesWritten:
      notes && typeof notes === "object"
        ? Object.values(notes).filter((value) => String(value ?? "").trim().length > 0).length
        : 0,
    commandsRun: Array.isArray(terminal) ? terminal.length : 0,
  };
}

function touched(activity: Activity): boolean {
  return (
    activity.answered > 0 ||
    activity.hintsRead > 0 ||
    activity.solutionRead ||
    activity.notesWritten > 0 ||
    activity.commandsRun > 0
  );
}

/** Plain phrases, in the order somebody would actually work through them. */
function describe(activity: Activity, entry: ProofEntry): string[] {
  const lines: string[] = [];
  const plural = (count: number, word: string) =>
    `${count} ${word}${count === 1 ? "" : "s"}`;

  if (activity.commandsRun > 0) {
    lines.push(`${plural(activity.commandsRun, "command")} replayed`);
  }
  if (activity.notesWritten > 0) {
    lines.push(`${activity.notesWritten} of ${SCRATCHPAD_STEPS} scratchpad steps written`);
  }
  if (activity.hintsRead > 0) {
    lines.push(`${activity.hintsRead} of ${entry.hintCount} hints opened`);
  }
  if (activity.solutionRead) lines.push("solution read");
  if (activity.answered > 0) {
    const answered = `${activity.answered} of ${entry.questionCount} questions answered`;
    lines.push(activity.score === null ? answered : `${answered}, ${activity.score} right`);
  }
  return lines;
}

export default function ProofRecord({ base, entries }: Props) {
  // Read after mount, never during render. These pages are prerendered and the
  // build has no localStorage, so reading during render would make the first
  // client render disagree with the HTML that was served. Same reasoning as
  // storage.ts, whose hook this page is too wide to use: that one is a single
  // key, and this reads six for each of twenty five exercises.
  const [loaded, setLoaded] = useState(false);
  const [activity, setActivity] = useState<Record<string, Activity>>({});
  const [completed, setCompleted] = useState<string[]>([]);
  const [pasted, setPasted] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const next: Record<string, Activity> = {};
    for (const entry of entries) next[entry.id] = readActivity(entry.id);
    setActivity(next);
    setCompleted(readJson<string[]>(KEY_COMPLETED, []).filter((id) => typeof id === "string"));
    setLoaded(true);
  }, []);

  const known = new Set(entries.map((entry) => entry.id));
  const proven = completed.filter((id) => known.has(id));

  /**
   * Accept the output of `tse progress --json`, or explain exactly why not.
   *
   * Nothing is written unless the whole payload parses and carries a list of
   * strings. A partial import that half succeeded would be worse than a
   * refusal, because this page would then be confidently wrong about work
   * somebody actually did.
   */
  function importProgress() {
    const text = pasted.trim();
    if (!text) {
      setMessage("Nothing pasted yet.");
      return;
    }

    let payload: unknown;
    try {
      payload = JSON.parse(text);
    } catch {
      setMessage(
        "That is not JSON. Run tse progress --json and paste everything it " +
          "prints, including the outer braces. Nothing was changed.",
      );
      return;
    }

    const list = (payload as { completed?: unknown } | null)?.completed;
    if (!Array.isArray(list) || list.some((id) => typeof id !== "string")) {
      setMessage(
        "That parsed as JSON but carries no completed list of exercise ids, so " +
          "it is not what tse progress --json prints. Nothing was changed.",
      );
      return;
    }

    const recognized = (list as string[]).filter((id) => known.has(id));
    const skipped = list.length - recognized.length;

    try {
      localStorage.setItem(KEY_COMPLETED, JSON.stringify(recognized));
    } catch {
      setMessage(
        "Your browser refused to store this, which private browsing usually " +
          "explains. Nothing was changed.",
      );
      return;
    }

    setCompleted(recognized);
    setPasted("");
    setMessage(
      `Imported ${recognized.length} completed exercise${recognized.length === 1 ? "" : "s"}.` +
        (skipped > 0
          ? ` ${skipped} id${skipped === 1 ? "" : "s"} went unrecognized and ` +
            `${skipped === 1 ? "was" : "were"} left out, which usually means your ` +
            `clone is older or newer than this site.`
          : ""),
    );
  }

  // Grouped in the order somebody is meant to work through them, which
  // loadExercises has already sorted the list into.
  const groups: { label: string; items: ProofEntry[] }[] = [];
  for (const entry of entries) {
    const last = groups[groups.length - 1];
    if (last && last.label === entry.trackLabel) last.items.push(entry);
    else groups.push({ label: entry.trackLabel, items: [entry] });
  }

  return (
    <section class="proof" aria-labelledby="proof-record-heading">
      {/*
        An h2, and not decoration. The page's own prose sits under its h1 and
        the track names below are h3, so without this the outline goes h1 to h3
        and skips a level. Screen reader users navigate a page this long by its
        headings, and the accessibility gate caught it on the first run.
      */}
      <h2 id="proof-record-heading">Where you are</h2>

      <p class="proof__count" role="status">
        {!loaded
          ? `${entries.length} exercises.`
          : proven.length === 0
            ? `Nothing imported, so none of the ${entries.length} questions below is ` +
              `answered on the only evidence that counts.`
            : `${proven.length} of ${entries.length} proven against a real system.`}
      </p>

      <div class="proof__import">
        <label class="proof__label" for="proof-paste">
          Paste the output of <code>tse progress --json</code>
        </label>
        <p class="proof__help" id="proof-paste-help">
          This is the only thing that can tell this page you fixed anything. It
          stays in your browser. There is no account and nothing is uploaded.
        </p>
        <textarea
          id="proof-paste"
          class="proof__textarea"
          rows={4}
          spellcheck={false}
          aria-describedby="proof-paste-help"
          value={pasted}
          onInput={(event) => setPasted((event.target as HTMLTextAreaElement).value)}
        />
        <div class="reveal__actions">
          <button type="button" class="reveal__button" onClick={importProgress}>
            Import
          </button>
          {proven.length > 0 && (
            <button
              type="button"
              class="reveal__button reveal__button--quiet"
              onClick={() => {
                try {
                  localStorage.removeItem(KEY_COMPLETED);
                } catch {
                  /* Nothing was stored to begin with. */
                }
                setCompleted([]);
                setMessage("Imported record cleared. Nothing else was touched.");
              }}
            >
              Clear imported record
            </button>
          )}
        </div>
        {message && (
          <p class="proof__message" role="status">
            {message}
          </p>
        )}
      </div>

      {groups.map((group) => (
        <section class="proof__track" key={group.label}>
          <h3>{group.label}</h3>
          <ul class="proof__list">
            {group.items.map((entry) => {
              const record = activity[entry.id];
              const isProven = proven.includes(entry.id);
              // Before the first read completes, `activity` is empty and every
              // item is correctly "Not started". Narrowing here rather than at
              // the point of use keeps the check and the value together.
              const notes = record && touched(record) ? describe(record, entry) : [];

              return (
                <li
                  key={entry.id}
                  class={isProven ? "proof__item proof__item--proven" : "proof__item"}
                >
                  <p class="proof__claim">
                    {isProven ? asStatement(entry.proofQuestion) : entry.proofQuestion}
                  </p>
                  <p class="proof__state">
                    {isProven ? (
                      <>
                        <span class="proof__mark" aria-hidden="true">
                          &#10003;
                        </span>
                        Proven. <code>tse check</code> passed this against a real system.
                      </>
                    ) : notes.length > 0 ? (
                      <>Worked on here: {notes.join(", ")}.</>
                    ) : (
                      "Not started."
                    )}
                  </p>
                  <p class="proof__link">
                    <a href={`${base}${entry.href}`}>{entry.title}</a>
                  </p>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </section>
  );
}
