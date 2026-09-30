import { Problem, statusLabels } from "../lib/types";

export function ProblemCard({ problem, onOpen }: { problem: Problem; onOpen: () => void }) {
  return <article className="card"><div><div className="badges">{problem.difficulty && <span>{problem.difficulty}</span>}<span className={problem.status}>{statusLabels[problem.status]}</span></div><h3>{problem.title}</h3><p className="muted">{problem.prompt}</p></div><button onClick={onOpen}>Open</button></article>;
}
