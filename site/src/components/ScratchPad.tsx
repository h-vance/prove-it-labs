import { useStored } from "./storage";

interface Field {
  key: string;
  label: string;
  help: string;
  rows: number;
}

/**
 * The seven-step investigation scratchpad, on the page and persistent.
 *
 * The reason it exists: holding a half-finished investigation in your head is
 * expensive, and it is the first thing to collapse under time pressure. Writing
 * the prediction down before running anything is what makes being wrong useful
 * rather than embarrassing.
 */
const FIELDS: Field[] = [
  {
    key: "symptom",
    label: "1. Customer symptom",
    help: "In their words, not yours. Include scope and urgency.",
    rows: 3,
  },
  {
    key: "prediction",
    label: "2. Prediction",
    help: "Before running anything: target layer, expected output, two likely causes.",
    rows: 4,
  },
  {
    key: "evidence",
    label: "3. Evidence gathered",
    help: "The command or query, and why it is safe to run here.",
    rows: 3,
  },
  {
    key: "reading",
    label: "4. Confirmed / disproven / still unknown",
    help: "Three separate lists. This is the step people skip.",
    rows: 5,
  },
  {
    key: "proof",
    label: "5. What it proves",
    help: "One proof sentence, one safe next step, one alternate hypothesis.",
    rows: 4,
  },
  {
    key: "wording",
    label: "6. Customer update and escalation note",
    help: "Plain language. Impact first. No blame, no speculation.",
    rows: 5,
  },
  {
    key: "recall",
    label: "7. Recall",
    help: "One gap, one command to repeat tomorrow, one confidence score.",
    rows: 3,
  },
];

type Entries = Record<string, string>;

export default function ScratchPad({ exerciseId }: { exerciseId: string }) {
  const [entries, setEntries] = useStored<Entries>(`proveit:scratchpad:${exerciseId}`, {});

  const set = (key: string, value: string) => setEntries({ ...entries, [key]: value });

  const filled = FIELDS.filter((field) => (entries[field.key] ?? "").trim().length > 0).length;

  const exportMarkdown = () => {
    const body = FIELDS.map(
      (field) => `## ${field.label}\n\n${(entries[field.key] ?? "").trim() || "_(blank)_"}`,
    ).join("\n\n");
    const document_ = `# Investigation: ${exerciseId}\n\n${body}\n`;

    navigator.clipboard?.writeText(document_).then(
      () => alert("Scratchpad copied to your clipboard as markdown."),
      () => alert("Could not access the clipboard. Select the text manually to copy it."),
    );
  };

  return (
    <section class="pad" aria-labelledby={`pad-${exerciseId}`}>
      <h2 id={`pad-${exerciseId}`}>Investigation scratchpad</h2>
      <p class="pad__lede">
        Saved in this browser as you type. Nothing is uploaded.{" "}
        <span role="status">
          {filled} of {FIELDS.length} filled in.
        </span>
      </p>

      {FIELDS.map((field) => {
        const id = `pad-${exerciseId}-${field.key}`;
        return (
          <div class="pad__field" key={field.key}>
            <label for={id}>{field.label}</label>
            <p class="pad__help" id={`${id}-help`}>
              {field.help}
            </p>
            <textarea
              id={id}
              rows={field.rows}
              aria-describedby={`${id}-help`}
              value={entries[field.key] ?? ""}
              onInput={(event) => set(field.key, (event.target as HTMLTextAreaElement).value)}
            />
          </div>
        );
      })}

      <div class="pad__actions">
        <button type="button" class="reveal__button" onClick={exportMarkdown}>
          Copy as markdown
        </button>
        <button
          type="button"
          class="reveal__button reveal__button--quiet"
          onClick={() => {
            if (confirm("Clear this scratchpad? This cannot be undone.")) setEntries({});
          }}
        >
          Clear
        </button>
      </div>
    </section>
  );
}
