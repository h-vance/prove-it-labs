import { useState } from "preact/hooks";

interface Option {
  label: string;
  score: Partial<Record<Track, number>>;
}
interface Question {
  id: string;
  prompt: string;
  options: Option[];
}
type Track = "docker" | "api";

interface Props {
  base: string;
  /** Passed in from the labs so this cannot recommend an exercise that is gone. */
  entryPoints: { track: Track; href: string; title: string }[];
}

const QUESTIONS: Question[] = [
  {
    id: "comfort",
    prompt: "How do you feel about a terminal?",
    options: [
      { label: "At home in one", score: { docker: 1, api: 1 } },
      { label: "Fine with commands I already know", score: { docker: 1, api: 1 } },
      { label: "It makes me nervous", score: { api: 2 } },
    ],
  },
  {
    id: "surface",
    prompt: "Which of these have you actually touched before?",
    options: [
      { label: "Containers, or something like them", score: { docker: 2 } },
      { label: "APIs, Postman, or webhooks", score: { api: 2 } },
      { label: "Neither, really", score: { api: 1 } },
    ],
  },
  {
    id: "goal",
    prompt: "What is the nearest thing you are preparing for?",
    options: [
      { label: "An interview with a live troubleshooting round", score: { docker: 2, api: 1 } },
      { label: "A support role I have already started", score: { api: 2, docker: 1 } },
      { label: "No deadline, I want the fundamentals", score: { docker: 1, api: 1 } },
    ],
  },
  {
    id: "energy",
    prompt: "Honestly, how much focus do you have right now?",
    options: [
      { label: "A clear couple of hours", score: { docker: 1, api: 1 } },
      { label: "Maybe half an hour", score: { api: 1 } },
      { label: "Very little, I just want to start something", score: { api: 1 } },
    ],
  },
];

export default function StartHere({ base, entryPoints }: Props) {
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const answered = Object.keys(answers).length;
  const complete = answered === QUESTIONS.length;

  const totals: Record<string, number> = {};
  for (const question of QUESTIONS) {
    const chosen = answers[question.id];
    if (chosen === undefined) continue;
    for (const [track, points] of Object.entries(question.options[chosen].score)) {
      totals[track] = (totals[track] ?? 0) + (points ?? 0);
    }
  }

  const ranked = entryPoints
    .map((entry) => ({ ...entry, score: totals[entry.track] ?? 0 }))
    .sort((a, b) => b.score - a.score);
  const winner = ranked[0];

  const lowEnergy = answers.energy === 2;

  return (
    <section class="start" aria-labelledby="start-heading">
      <h2 id="start-heading">Where should I begin?</h2>
      <p class="start__lede">
        Four questions. There is no wrong entry point, and you can change tracks
        whenever you like. This exists so that picking one is not the thing that
        stops you.
      </p>

      {QUESTIONS.map((question, questionIndex) => (
        <fieldset class="start__question" key={question.id}>
          <legend>
            {questionIndex + 1}. {question.prompt}
          </legend>
          {question.options.map((option, optionIndex) => (
            <label class="start__option" key={option.label}>
              <input
                type="radio"
                name={question.id}
                checked={answers[question.id] === optionIndex}
                onChange={() => setAnswers({ ...answers, [question.id]: optionIndex })}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </fieldset>
      ))}

      <div class="start__result" role="status" aria-live="polite">
        {complete && winner ? (
          <>
            <h3>Start with {winner.title}</h3>
            <p>
              {winner.track === "docker"
                ? "The Docker track builds the habit everything else depends on: proving whether something is running before explaining why it is not."
                : "The API track needs no container knowledge and gives the fastest feedback loop, which makes it a gentler place to build the evidence habit."}
            </p>
            {lowEnergy && (
              <p class="start__note">
                You said focus is short today, so use the minimum viable day: one
                ticket, one command, one proof sentence. That counts. Stop there
                without guilt.
              </p>
            )}
            <p>
              <a class="start__cta" href={`${base}${winner.href}`}>
                Open {winner.title}
              </a>
            </p>
          </>
        ) : (
          <p class="start__pending">
            {answered} of {QUESTIONS.length} answered.
          </p>
        )}
      </div>
    </section>
  );
}
