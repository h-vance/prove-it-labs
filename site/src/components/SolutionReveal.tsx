import { useStored } from "./storage";

interface Props {
  exerciseId: string;
  solution: string;
}

/**
 * The solution stays behind one deliberate click.
 *
 * Not to gatekeep. It is in the public repository and anyone can read it. The
 * click exists so nobody reads the answer by accident while scrolling, which
 * is the only way this page could actually harm someone's learning.
 *
 * One button rather than two, and it never unmounts. Written as a pair of
 * buttons in two branches, the one being pressed was removed from the page in
 * the same render, so focus fell back to the document body and the next Tab
 * started again from the top. That is invisible with a mouse and it happened
 * every time anybody opened or closed a solution with a keyboard.
 */
export default function SolutionReveal({ exerciseId, solution }: Props) {
  const [open, setOpen] = useStored(`proveit:solution:${exerciseId}`, false);
  const bodyId = `solution-body-${exerciseId}`;

  return (
    <section class="reveal" aria-labelledby={`solution-${exerciseId}`}>
      <h2 id={`solution-${exerciseId}`}>Solution</h2>

      {!open && (
        <p class="reveal__lede">
          Write your customer update before you read this. Comparing your
          wording against the model answer is worth more than reading it cold.
        </p>
      )}

      <div class="reveal__actions">
        <button
          type="button"
          class={`reveal__button${open ? " reveal__button--quiet" : ""}`}
          // The trigger says whether the thing it controls is open. Without
          // this a screen reader hears only the label change, which is the
          // difference between being told the state and inferring it.
          aria-expanded={open}
          aria-controls={bodyId}
          onClick={() => setOpen(!open)}
        >
          {open ? "Hide the solution" : "Reveal the solution"}
        </button>
      </div>

      {/* Always rendered, so aria-controls above always points at something
          real. Empty when closed rather than absent. */}
      <div id={bodyId} class="reveal__item">
        {open && <div dangerouslySetInnerHTML={{ __html: solution }} />}
      </div>
    </section>
  );
}
