"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ProblemWorkspace } from "./problem-workspace";
import { request } from "../lib/api";
import { Problem } from "../lib/types";

const value = (data: FormData, key: string) => data.get(key)?.toString().trim() || undefined;

export function ProblemSubmissionPage({ problemId }: { problemId: string }) {
  const [problem, setProblem] = useState<Problem>();
  const [error, setError] = useState("");
  useEffect(() => { void request(`/problems/${problemId}`).then(setProblem).catch(() => setError("Could not load this problem.")); }, [problemId]);

  const update = (next: Problem) => setProblem(next);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!problem) return;
    const data = new FormData(event.currentTarget);
    const submission = await request(`/problems/${problem.id}/submissions`, { method: "POST", body: JSON.stringify({ code: value(data, "code"), timeComplexity: value(data, "time"), spaceComplexity: value(data, "space"), explanation: value(data, "explanation") }) });
    update({ ...problem, status: "attempted", latestSubmission: submission });
  };
  const review = async () => {
    if (!problem?.latestSubmission) return;
    const submission = await request(`/submissions/${problem.latestSubmission.id}/review`, { method: "POST" });
    update({ ...problem, status: submission.evaluation.retryRecommended ? "reviewed_needs_retry" : "reviewed_complete", latestSubmission: submission });
  };

  if (error) return <main><Link href="/">Back to dashboard</Link><p className="error">{error}</p></main>;
  if (!problem) return <main><p className="muted">Loading problem…</p></main>;
  return <main><ProblemWorkspace problem={problem} onClose={() => window.history.back()} onSubmit={submit} onReview={() => void review()} /></main>;
}
