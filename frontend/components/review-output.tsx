import { Evaluation, Submission } from "../lib/types";

export function ReviewOutput({ submission, onRequest }: { submission?: Submission; onRequest: () => void }) {
  const evaluation = submission?.evaluation;
  return <section className="review-output"><div className="heading"><div><p className="eyebrow">AGENT REVIEW</p><h3>Structured feedback</h3></div><button disabled={!submission} onClick={onRequest}>Request review</button></div>{evaluation ? <Feedback evaluation={evaluation} /> : <p className="muted">Submit a solution, then request a backend agent review.</p>}</section>;
}

function Feedback({ evaluation }: { evaluation: Evaluation }) {
  const fields = [["Completeness", evaluation.completeness], ["Correctness", evaluation.correctness], ["Bugs / missed edge cases", evaluation.bugsAndEdgeCases], ["Complexity analysis", evaluation.complexityAnalysis], ["Reasoning quality", evaluation.reasoningQuality], ["Cleaner / better approach", evaluation.betterApproach], ["Concept tags", evaluation.conceptTags?.join(", ")], ["Notes", evaluation.notes]].filter(([, content]) => content);
  return <dl><div><dt>Needs retry</dt><dd>{evaluation.retryRecommended ? "Yes" : "No"}</dd></div>{fields.map(([label, content]) => <div key={label}><dt>{label}</dt><dd>{content}</dd></div>)}</dl>;
}
