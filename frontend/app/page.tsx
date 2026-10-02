"use client";

import { FormEvent, useEffect, useState } from "react";
import { ProblemCard } from "../components/problem-card";
import { ProblemWorkspace } from "../components/problem-workspace";
import { LoginForm } from "../components/login-form";
import { clearSessionCredentials, hasSessionCredentials, request, saveSessionCredentials } from "../lib/api";
import { Plan, Problem } from "../lib/types";

const value = (data: FormData, key: string) => data.get(key)?.toString().trim() || undefined;

export default function Page() {
  const [plan, setPlan] = useState<Plan>();
  const [active, setActive] = useState<Problem>();
  const [error, setError] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const load = () => request("/daily").then(setPlan).catch((requestError) => {
    setError(requestError.status === 401 ? "Your session expired. Sign in again." : "Could not reach the API.");
    if (requestError.status === 401) setAuthenticated(false);
  });
  useEffect(() => { if (hasSessionCredentials()) setAuthenticated(true); }, []);
  useEffect(() => { if (authenticated && !plan) void load(); }, [authenticated, plan]);

  const login = async (username: string, password: string) => {
    saveSessionCredentials(username, password);
    const daily = await request("/daily");
    setPlan(daily);
    setAuthenticated(true);
  };

  const update = (problem: Problem) => {
    setActive(problem);
    setPlan((current) => current && { problems: current.problems.map((item) => item.id === problem.id ? problem : item) });
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!active) return;
    const data = new FormData(event.currentTarget);
    const submission = await request(`/problems/${active.id}/submissions`, { method: "POST", body: JSON.stringify({ code: value(data, "code"), timeComplexity: value(data, "time"), spaceComplexity: value(data, "space"), explanation: value(data, "explanation") }) });
    update({ ...active, status: "attempted", latestSubmission: submission });
  };
  const review = async () => {
    if (!active?.latestSubmission) return;
    const submission = await request(`/submissions/${active.latestSubmission.id}/review`, { method: "POST" });
    update({ ...active, status: submission.evaluation.retryRecommended ? "reviewed_needs_retry" : "reviewed_complete", latestSubmission: submission });
  };
  const complete = plan?.problems.filter((problem) => problem.status === "reviewed_complete").length || 0;

  if (!authenticated) return <LoginForm onLogin={login} />;
  return <main><header><div><p className="eyebrow">INTERVIEW PREP</p><h1>Daily console</h1><p className="muted">{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date())}</p></div><div className="actions"><button onClick={() => request("/daily/refresh", { method: "POST" }).then(setPlan)}>New set for today</button><button onClick={() => { clearSessionCredentials(); setPlan(undefined); setActive(undefined); setAuthenticated(false); }}>Sign out</button></div></header><section><div className="heading"><div><p className="eyebrow">TODAY</p><h2>Your problem set</h2></div><p className="muted">{complete} of {plan?.problems.length || 0} reviewed complete</p></div>{error && <p className="error">{error}</p>}<div className="cards">{plan?.problems.map((problem) => <ProblemCard key={problem.id} problem={problem} onOpen={() => setActive(problem)} />)}</div></section>{active && <ProblemWorkspace problem={active} onClose={() => setActive(undefined)} onSubmit={submit} onReview={() => void review()} />}</main>;
}
