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
 */
export default function SolutionReveal({ exerciseId, solution }: Props) {
  const [open, setOpen] = useStored(`proveit:solution:${exerciseId}`, false);

  return (
    <section class="reveal" aria-labelledby={`solution-${exerciseId}`}>
      <h2 id={`solution-${exerciseId}`}>Solution</h2>

      {open ? (
        <>
          <div class="reveal__item" dangerouslySetInnerHTML={{ __html: solution }} />
          <div class="reveal__actions">
            <button type="button" class="reveal__button reveal__button--quiet" onClick={() => setOpen(false)}>
              Hide the solution
            </button>
          </div>
        </>
      ) : (
        <div class="reveal__actions">
          <p class="reveal__lede">
            Write your customer update before you read this. Comparing your
            wording against the model answer is worth more than reading it cold.
          </p>
          <button type="button" class="reveal__button" onClick={() => setOpen(true)}>
            Reveal the solution
          </button>
        </div>
      )}
    </section>
  );
}
