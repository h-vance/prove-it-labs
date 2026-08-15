import { useEffect, useMemo, useRef, useState } from "preact/hooks";
import { useStored } from "./storage";
import type { TranscriptEntry } from "../lib/labs";

interface Props {
  exerciseId: string;
  entries: TranscriptEntry[];
}

type Kind = "output" | "refusal" | "note";

interface Line {
  /** What the learner typed, echoed back exactly as they typed it. */
  typed: string;
  kind: Kind;
  body: string;
  exit?: number;
}

/**
 * Collapse a typed command to the form recorded entries are keyed by.
 *
 * The twin of normalize_command in tools/tse. Both are asserted against
 * tools/tests/fixtures/normalize.json, this one by driving the built page, so
 * the two cannot drift apart while their test suites stay green.
 */
export function normalize(command: string): string {
  return command
    .replace(/\\\s*\n/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .join(" ");
}

/** Commands whose whole purpose is to state the answer or grade the fix. */
const GRADING = /^tse\s+(answer|hint|check|quiz)\b/;
const PROVISIONING = /^tse\s+(start|apply|reset|stop|record|verify)\b/;

const REFUSALS: { test: RegExp; body: string }[] = [
  {
    test: GRADING,
    body:
      "Not here, and not by accident.\n\n" +
      "Grading states what the fixed system should look like in order to check it, so " +
      "replaying that output would hand over the diagnosis. The hints and the solution " +
      "are already on this page, behind buttons you choose to press.\n\n" +
      "Run it against a system you actually changed:  tse check",
  },
  {
    test: PROVISIONING,
    body:
      "That one starts and stops real containers, which a page cannot do.\n\n" +
      "This terminal replays output that was captured from the running labs. It is a " +
      "way to see what the evidence looks like before you commit to setting anything " +
      "up, not a substitute for doing so.",
  },
];

const HELP =
  "This is a replay, not a shell.\n\n" +
  "Every command it knows was run against the real broken system and its output " +
  "captured, so what you see here is what you would have seen. Nothing you type " +
  "changes anything, and nothing here can finish the exercise.\n\n" +
  "  help     this text\n" +
  "  clear    empty the screen\n" +
  "  reset    empty the screen and forget what you have typed\n\n" +
  "Up and down arrows walk back through your own commands. Shift and Enter start " +
  "a new line, so a command copied across three lines pastes in as one.";

export default function LabTerminal({ exerciseId, entries }: Props) {
  // Which commands were typed persists; the output on screen does not. The
  // output is one keystroke away from coming back, and storing it would copy
  // the whole transcript into someone's browser for nothing.
  const [history, setHistory] = useStored<string[]>(`proveit:terminal:${exerciseId}`, []);
  const [revealed, setRevealed] = useStored(`proveit:terminal-list:${exerciseId}`, 0);
  const [lines, setLines] = useState<Line[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("");
  // -1 means "not walking history", which is a different state from index 0.
  const [walked, setWalked] = useState(-1);
  const field = useRef<HTMLTextAreaElement>(null);

  const index = useMemo(() => {
    const map = new Map<string, TranscriptEntry>();
    for (const entry of entries) {
      for (const key of entry.match) map.set(key, entry);
    }
    return map;
  }, [entries]);

  // Grow with the content. A command pasted across three lines should be
  // visible as three lines rather than hidden behind a scrollbar in a one-line
  // box, since joining those lines is exactly what this field has to get right.
  useEffect(() => {
    const node = field.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${node.scrollHeight}px`;
  }, [draft]);

  if (entries.length === 0) return null;

  /**
   * Does something close to this exist?
   *
   * Answering a flat "no" to a singular/plural slip reads as the terminal being
   * broken, so a near miss says something close was recorded without saying
   * what. That gives away nothing the reveal button below does not.
   *
   * Two leading tokens in common, except that a recorded command shorter than
   * that only has to match as far as it goes. A fixed two-token prefix looked
   * right until `./request.sh` turned up: one token long, so `./request.sh
   * --verbose` could never share two tokens with it and fell through to the
   * flat refusal, which is the case the nudge exists for.
   */
  function nearMiss(typed: string): boolean {
    const typedTokens = typed.split(" ");
    for (const key of index.keys()) {
      if (key === typed) continue;
      const keyTokens = key.split(" ");
      let shared = 0;
      while (
        shared < typedTokens.length &&
        shared < keyTokens.length &&
        typedTokens[shared] === keyTokens[shared]
      ) {
        shared += 1;
      }
      if (shared >= Math.min(2, typedTokens.length, keyTokens.length)) return true;
    }
    return false;
  }

  function push(line: Line, announced: string) {
    setLines((previous) => [...previous, line]);
    setStatus(announced);
  }

  function run(raw: string) {
    const typed = raw.trim();
    if (!typed) return;

    setHistory((previous) => (previous[previous.length - 1] === typed ? previous : [...previous, typed]));
    setDraft("");
    setWalked(-1);

    const command = normalize(typed);

    if (command === "clear" || command === "reset") {
      setLines([]);
      if (command === "reset") setHistory([]);
      setStatus(command === "reset" ? "Screen and history cleared." : "Screen cleared.");
      return;
    }

    if (command === "help") {
      push({ typed, kind: "note", body: HELP }, "Showing what this terminal can do.");
      return;
    }

    for (const refusal of REFUSALS) {
      if (refusal.test.test(command)) {
        push({ typed, kind: "refusal", body: refusal.body }, "That one is not replayed here.");
        return;
      }
    }

    const entry = index.get(command);
    if (entry) {
      const count = entry.output.split("\n").length;
      push(
        { typed, kind: "output", body: entry.output, exit: entry.exit },
        `${count} ${count === 1 ? "line" : "lines"} of output, exit status ${entry.exit}.`,
      );
      return;
    }

    push(
      {
        typed,
        kind: "refusal",
        body: nearMiss(command)
          ? "Nothing recorded for exactly that. Something close is, so it is worth " +
            "another look at how you spelled it."
          : "Nothing recorded for that.\n\nOnly the commands that were actually run " +
            "against this exercise have output to show. Inventing the rest would make " +
            "this a walkthrough that happens to look like a terminal.",
      },
      "Nothing recorded for that command.",
    );
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      run(draft);
      return;
    }
    // Only take the arrows while the field holds a single line. In a wrapped
    // command they belong to the caret, and stealing them there would make a
    // multi-line paste impossible to edit.
    if (draft.includes("\n") || history.length === 0) return;

    if (event.key === "ArrowUp") {
      event.preventDefault();
      const next = walked === -1 ? history.length - 1 : Math.max(0, walked - 1);
      setWalked(next);
      // The index is bounded on the line above, so this can only be undefined
      // if the history emptied in between. An empty draft is what walking off
      // the end of the list does anyway.
      setDraft(history[next] ?? "");
    } else if (event.key === "ArrowDown") {
      if (walked === -1) return;
      event.preventDefault();
      const next = walked + 1;
      if (next >= history.length) {
        setWalked(-1);
        setDraft("");
      } else {
        setWalked(next);
        setDraft(history[next] ?? "");
      }
    }
  }

  return (
    <section class="terminal" aria-labelledby={`terminal-${exerciseId}`}>
      <h2 id={`terminal-${exerciseId}`}>Look at the evidence</h2>
      <p class="reveal__lede">
        Real output, captured by running these commands against the broken system
        and checked against it on every build. It shows you what the evidence looks
        like. It cannot fix anything, and it will not tell you what is wrong.
      </p>

      <div class="terminal__screen">
        {lines.length === 0 ? (
          <p class="terminal__idle">
            Type a command you would reach for, or <code>help</code>.
          </p>
        ) : (
          lines.map((line, position) => (
            <div class="terminal__entry" key={position}>
              <p class="terminal__echo">
                <span class="terminal__prompt" aria-hidden="true">
                  $
                </span>
                <span class="terminal__typed">{line.typed}</span>
              </p>
              {line.kind === "output" ? (
                // Focusable and named, because a box that scrolls has to be
                // reachable from a keyboard, and because a screen reader
                // otherwise meets an unlabeled slab of text.
                <pre
                  class="terminal__output"
                  tabIndex={0}
                  role="group"
                  aria-label={`Output of ${line.typed}`}
                >
                  {line.body}
                </pre>
              ) : (
                <p class={`terminal__${line.kind}`}>{line.body}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/*
        The announcement is one line, deliberately. Putting the output itself in
        a live region would read twenty lines of table aloud on every command,
        which is punishing rather than helpful. The output is next to it, named
        and focusable, for anyone who wants to go through it.
      */}
      <p class="terminal__status" role="status">
        {status}
      </p>

      <div class="terminal__input">
        <label for={`terminal-field-${exerciseId}`}>Command</label>
        <textarea
          id={`terminal-field-${exerciseId}`}
          ref={field}
          class="terminal__field"
          rows={1}
          spellcheck={false}
          autocomplete="off"
          aria-describedby={`terminal-help-${exerciseId}`}
          value={draft}
          onInput={(event) => setDraft((event.target as HTMLTextAreaElement).value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          class="reveal__button"
          onClick={() => {
            run(draft);
            field.current?.focus();
          }}
        >
          Run
        </button>
      </div>
      <p id={`terminal-help-${exerciseId}`} class="terminal__hint">
        Enter runs it. Shift and Enter start a new line. The up and down arrows walk
        back through what you have typed.
      </p>

      {/*
        One button that stays put, matching the hints and the solution.

        This was a button in one branch and a `<details>` in the other, so the
        element being clicked was gone by the time the click finished and focus
        fell back to the document body. With a mouse that is invisible. With a
        keyboard it means the next Tab starts again from the top of the page,
        every time anybody opened this.
      */}
      <div class="reveal__actions">
        <button
          type="button"
          class="reveal__button reveal__button--quiet"
          aria-expanded={revealed > 0}
          aria-controls={`terminal-recorded-${exerciseId}`}
          onClick={() => setRevealed(revealed > 0 ? 0 : 1)}
        >
          {revealed > 0
            ? `The ${entries.length} commands with recorded output`
            : "Show which commands are recorded"}
          {revealed === 0 && (
            <span class="reveal__count"> (this is close to a hint)</span>
          )}
        </button>
      </div>

      <div id={`terminal-recorded-${exerciseId}`} class="terminal__list">
        {revealed > 0 && (
          <ul>
            {/*
              Normalized rather than as written. commands.txt wraps long
              commands with backslashes, and HTML collapses those newlines
              into one run-on line with a stray backslash in the middle. The
              single-line form is also the one worth showing, because it is
              the one somebody can type straight back in.
            */}
            {entries.map((entry) => (
              <li key={entry.command}>
                <code>{normalize(entry.command)}</code>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
