import { FormEvent } from "react";
import { Problem } from "../lib/types";
import { ProblemPrompt } from "./problem-prompt";
import { ReviewOutput } from "./review-output";
import { SubmissionForm } from "./submission-form";

export function ProblemWorkspace({ problem, onClose, onSubmit, onReview }: { problem: Problem; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; onReview: () => void }) {
  const metadata = [problem.difficulty, ...(problem.topics || [])].filter(Boolean).join(" · ");
  return <section className="workspace"><div className="heading"><div>{metadata && <p className="eyebrow">{metadata}</p>}<h2>{problem.sourceId && `#${problem.sourceId} · `}{problem.title}</h2></div><button onClick={onClose}>Close</button></div><ProblemPrompt html={problem.prompt} />{problem.link && <a href={problem.link} target="_blank" rel="noreferrer">Open original problem</a>}<SubmissionForm submission={problem.latestSubmission} starterCode={problem.starterCode} onSubmit={onSubmit} /><ReviewOutput submission={problem.latestSubmission} onRequest={onReview} /></section>;
}
