import Link from "next/link";
import { Problem, statusLabels } from "../lib/types";

export function ProblemCard({ problem }: { problem: Problem }) {
  const difficultyClass = problem.difficulty?.toLowerCase();
  return <article className="card"><div><div className="badges">{problem.difficulty && <span className={difficultyClass}>{problem.difficulty}</span>}<span className={problem.status}>{statusLabels[problem.status]}</span></div><h3>{problem.sourceId && `#${problem.sourceId} · `}{problem.title}</h3><p className="muted">{problem.prompt.replace(/<[^>]+>/g, " ")}</p></div><Link className="open-link" href={`/problems/${problem.id}`}>Open</Link></article>;
}
