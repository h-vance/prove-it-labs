import { useRef } from "preact/hooks";
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
 *
 * The reveal button stays mounted for every state, including the one where
 * there is nothing left to reveal. It used to be replaced by a paragraph on the
 * last click, which meant the button being pressed vanished mid-render and
 * focus fell back to the document body. "Hide hints" had the same shape and
 * hands focus back explicitly instead, since it genuinely has nowhere to stay.
 */
export default function HintReveal({ exerciseId, hints }: Props) {
  const [shown, setShown] = useStored(`proveit:hints:${exerciseId}`, 0);
  const revealRef = useRef<HTMLButtonElement>(null);

  if (hints.length === 0) return null;
  const remaining = hints.length - shown;
  const exhausted = remaining === 0;

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
        <button
          type="button"
          class="reveal__button"
          ref={revealRef}
          aria-disabled={exhausted}
          onClick={() => {
            if (exhausted) return;
            setShown((n) => n + 1);
          }}
        >
          {exhausted
            ? `All ${hints.length} hints shown`
            : shown === 0
              ? "Show the first hint"
              : `Show hint ${shown + 1}`}
          {!exhausted && <span class="reveal__count"> ({remaining} left)</span>}
        </button>

        {shown > 0 && (
          <button
            type="button"
            class="reveal__button reveal__button--quiet"
            onClick={() => {
              setShown(0);
              // This button is about to be removed from the page. Handing focus
              // to the one beside it keeps the learner's place instead of
              // dropping them at the top of the document.
              revealRef.current?.focus();
            }}
          >
            Hide hints
          </button>
        )}
      </div>

      {/* Rendered whether or not anything has been shown, so its text changing
          is what a screen reader announces. A region that appears at the same
          moment its message does is announced unreliably. */}
      <p class="reveal__done" role="status">
        {shown === 0
          ? ""
          : exhausted
            ? `All ${hints.length} hints shown.`
            : `Hint ${shown} of ${hints.length} shown.`}
      </p>
    </section>
  );
}
