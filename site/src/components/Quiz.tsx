import { useStored } from "./storage";
import type { QuizQuestion } from "../lib/labs";

interface Props {
  exerciseId: string;
  questions: QuizQuestion[];
}

const UNANSWERED = -1;

/**
 * The questions that replaced the spoken answer at the end of every solution.
 *
 * Three rules this component exists to keep:
 *
 *  - Feedback never rests on color. Every verdict carries a symbol and a word
 *    as well, so it survives a monochrome display, a color vision deficiency,
 *    and a screen reader equally.
 *  - The explanation is not a reward for being wrong. It appears on a correct
 *    answer too, because a learner who guessed and was told only "correct" has
 *    learned nothing and does not know they guessed.
 *  - Answering is one click and cannot be taken back per question. Letting
 *    someone cycle options until the page goes green turns a check of
 *    understanding into a game of pattern matching.
 */
export default function Quiz({ exerciseId, questions }: Props) {
  const [answers, setAnswers] = useStored<number[]>(
    `proveit:quiz:${exerciseId}`,
    questions.map(() => UNANSWERED),
  );

  if (questions.length === 0) return null;

  // Stored state can be shorter than the question list if questions were added
  // after someone last visited. Pad rather than throwing their progress away.
  const chosen = questions.map((_, index) => answers[index] ?? UNANSWERED);
  const answered = chosen.filter((value) => value !== UNANSWERED).length;
  // `pick` is read into a local first. Indexing twice in one expression means
  // the compiler cannot carry the "this is a real answer" check across to the
  // options lookup, and the score is the one number on this page a learner
  // would take at face value.
  const score = questions.filter((question, index) => {
    const pick = chosen[index];
    return pick !== undefined && pick !== UNANSWERED && question.options[pick]?.correct;
  }).length;

  // Functional update, not setAnswers([...chosen]). Two answers given before
  // the next render would otherwise both build from the same stale array and
  // the first would be lost.
  function choose(questionIndex: number, optionIndex: number) {
    setAnswers((previous) => {
      const next = questions.map((_, index) => previous[index] ?? UNANSWERED);
      if (next[questionIndex] !== UNANSWERED) return previous;
      next[questionIndex] = optionIndex;
      return next;
    });
  }

  return (
    <section class="quiz" aria-labelledby={`quiz-${exerciseId}`}>
      <h2 id={`quiz-${exerciseId}`}>Check your understanding</h2>
      <p class="reveal__lede">
        Three questions on what the evidence proved and what it did not. Every
        answer explains itself, including the right one.
      </p>

      {questions.map((question, questionIndex) => {
        const pick = chosen[questionIndex];
        const isAnswered = pick !== undefined && pick !== UNANSWERED;
        const picked = isAnswered ? question.options[pick] : null;
        const isCorrect = Boolean(picked?.correct);
        const answer = question.options.find((option) => option.correct);

        return (
          <fieldset class="quiz__question" key={questionIndex}>
            <legend class="quiz__legend">
              <span class="quiz__number">
                Question {questionIndex + 1} of {questions.length}
              </span>
              {question.question}
            </legend>

            <ul class="quiz__options">
              {question.options.map((option, optionIndex) => {
                const isPick = isAnswered && optionIndex === pick;
                const isAnswerRow = isAnswered && option.correct;
                let state = "";
                if (isPick && isCorrect) state = " quiz__option--correct";
                else if (isPick) state = " quiz__option--wrong";
                else if (isAnswerRow) state = " quiz__option--answer";

                return (
                  <li key={optionIndex}>
                    <button
                      type="button"
                      class={`quiz__option${state}`}
                      onClick={() => choose(questionIndex, optionIndex)}
                      aria-pressed={isAnswered ? isPick : undefined}
                      // aria-disabled, not disabled. A browser cannot keep
                      // focus on a disabled element, so marking the button the
                      // learner just pressed as disabled dropped focus to the
                      // body, and the next Tab restarted from the top of the
                      // page. That happened on every question of every
                      // exercise, and only to people using a keyboard, which
                      // is why looking at the screen never showed it.
                      //
                      // Nothing is reopened by this. `choose` already refuses a
                      // second answer to the same question, and did before.
                      aria-disabled={isAnswered}
                    >
                      <span class="quiz__marker" aria-hidden="true">
                        {isPick && isCorrect ? "✓" : isPick ? "✗" : isAnswerRow ? "✓" : ""}
                      </span>
                      <span>{option.text}</span>
                      {isAnswerRow && !isPick && (
                        <span class="quiz__tag"> (the answer)</span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>

            {isAnswered && (
              <div
                class={`quiz__feedback quiz__feedback--${isCorrect ? "correct" : "wrong"}`}
                role="status"
              >
                <p class="quiz__verdict">
                  <span class="quiz__marker" aria-hidden="true">
                    {isCorrect ? "✓" : "✗"}
                  </span>
                  {isCorrect ? "Correct." : "Not quite."}
                </p>
                <p>{picked?.explanation}</p>
                {!isCorrect && answer && (
                  <>
                    <p class="quiz__verdict">The answer: {answer.text}</p>
                    <p>{answer.explanation}</p>
                  </>
                )}
              </div>
            )}
          </fieldset>
        );
      })}

      <div class="reveal__actions">
        <p class="quiz__score" role="status">
          {answered === 0
            ? `${questions.length} questions, none answered yet.`
            : answered < questions.length
              ? `${score} of ${answered} so far, ${questions.length - answered} to go.`
              : score === questions.length
                ? `${score} of ${questions.length}. You can explain this one, not just fix it.`
                : `${score} of ${questions.length}. Re-read the solution on the ones you missed.`}
        </p>
        {answered > 0 && (
          <button
            type="button"
            class="reveal__button reveal__button--quiet"
            onClick={() => setAnswers(questions.map(() => UNANSWERED))}
          >
            Start over
          </button>
        )}
      </div>
    </section>
  );
}
