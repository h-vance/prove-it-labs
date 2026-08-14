import { useStored } from "./storage";

interface Props {
  exerciseId: string;
  hints: string[];
}

/**
 * Hints one at a time, in the same order the CLI gives them.
 *
 * Revealing them all at once would turn the page into a walkthrough. Revealing
 * them one at a time keeps the decision to look at the learner, which is the
 * point: knowing you are stuck is a skill too.
 */
export default function HintReveal({ exerciseId, hints }: Props) {
  const [shown, setShown] = useStored(`proveit:hints:${exerciseId}`, 0);

  if (hints.length === 0) return null;
  const remaining = hints.length - shown;

  return (
    <section class="reveal" aria-labelledby={`hints-${exerciseId}`}>
      <h2 id={`hints-${exerciseId}`}>Hints</h2>
      <p class="reveal__lede">
        Each hint gives away a little more. Try to spend a few minutes on your
        own evidence first, because the recall is what makes it stick.
      </p>

      {hints.slice(0, shown).map((html, index) => (
        <article class="reveal__item" key={index}>
          <h3>
            Hint {index + 1}
            <span class="reveal__of"> of {hints.length}</span>
          </h3>
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </article>
      ))}

      <div class="reveal__actions">
        {remaining > 0 ? (
          <button type="button" class="reveal__button" onClick={() => setShown((n) => n + 1)}>
            {shown === 0 ? "Show the first hint" : `Show hint ${shown + 1}`}
            <span class="reveal__count"> ({remaining} left)</span>
          </button>
        ) : (
          <p class="reveal__done" role="status">
            All {hints.length} hints shown.
          </p>
        )}

        {shown > 0 && (
          <button type="button" class="reveal__button reveal__button--quiet" onClick={() => setShown(0)}>
            Hide hints
          </button>
        )}
      </div>
    </section>
  );
}
