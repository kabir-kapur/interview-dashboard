import { FormEvent } from "react";
import { Problem } from "../lib/types";
import { ReviewOutput } from "./review-output";
import { SubmissionForm } from "./submission-form";

export function ProblemWorkspace({ problem, onClose, onSubmit, onReview }: { problem: Problem; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; onReview: () => void }) {
  return <section className="workspace"><div className="heading"><div><p className="eyebrow">{problem.difficulty} · {problem.topics.join(" / ")}</p><h2>{problem.title}</h2></div><button onClick={onClose}>Close</button></div><p className="full">{problem.prompt}</p>{problem.link && <a href={problem.link}>Open original problem</a>}<SubmissionForm submission={problem.latestSubmission} onSubmit={onSubmit} /><ReviewOutput submission={problem.latestSubmission} onRequest={onReview} /></section>;
}
