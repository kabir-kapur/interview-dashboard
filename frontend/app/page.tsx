"use client";

import { FormEvent, useEffect, useState } from "react";
import { ProblemCard } from "../components/problem-card";
import { LoginForm } from "../components/login-form";
import { clearSessionCredentials, hasSessionCredentials, request, saveSessionCredentials } from "../lib/api";
import { Plan } from "../lib/types";

const value = (data: FormData, key: string) => data.get(key)?.toString().trim() || undefined;

export default function Page() {
  const [plan, setPlan] = useState<Plan>();
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
    await request("/session");
    setAuthenticated(true);
  };

  const complete = plan?.problems.filter((problem) => problem.status === "reviewed_complete").length || 0;

  if (!authenticated) return <LoginForm onLogin={login} />;
  return <main><header><div><p className="eyebrow">INTERVIEW PREP</p><h1>Daily console</h1><p className="muted">{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date())}</p></div><div className="actions"><button onClick={() => request("/daily/refresh", { method: "POST" }).then(setPlan)}>New set for today</button><button onClick={() => { clearSessionCredentials(); setPlan(undefined); setAuthenticated(false); }}>Sign out</button></div></header><section><div className="heading"><div><p className="eyebrow">TODAY</p><h2>Your problem set</h2></div><p className="muted">{complete} of {plan?.problems.length || 0} reviewed complete</p></div>{error && <p className="error">{error}</p>}<div className="cards">{plan?.problems.map((problem) => <ProblemCard key={problem.id} problem={problem} />)}</div></section></main>;
}
