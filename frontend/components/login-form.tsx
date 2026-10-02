"use client";

import { FormEvent, useState } from "react";

export function LoginForm({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    setError("");
    try {
      await onLogin(String(data.get("username")), String(data.get("password")));
    } catch {
      setError("Those credentials were not accepted.");
    } finally {
      setLoading(false);
    }
  };

  return <main className="login"><section><p className="eyebrow">INTERVIEW PREP</p><h1>Daily console</h1><p className="muted">Sign in to load your problem set.</p><form onSubmit={submit}><label>Username<input name="username" autoComplete="username" required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <p className="error">{error}</p>}<button disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button></form></section></main>;
}
