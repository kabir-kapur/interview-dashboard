"use client";

import { FormEvent, useState } from "react";
import { ApiError } from "../lib/api";

export function LoginForm({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    setError("");
    try {
      await onLogin(String(data.get("username")), String(data.get("password")));
    } catch (loginError) {
      setError(loginError instanceof ApiError && loginError.status === 401 ? "Those credentials were not accepted." : "The API could not load your problem set. Try again after it recovers.");
    } finally {
      setLoading(false);
    }
  };

  return <main className="login"><section><p className="eyebrow">INTERVIEW PREP</p><h1>Daily console</h1><p className="muted">Sign in to load your problem set.</p><form onSubmit={submit}><label>Username<input name="username" autoComplete="username" required /></label><label>Password<input name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" required /></label><button className="password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)}>{showPassword ? "Hide password" : "Show password"}</button>{error && <p className="error">{error}</p>}<button disabled={loading}>{loading ? "Signing in…" : "Sign in"}</button></form><p className="credential-help">To change credentials, update <code>BASIC_AUTH_USERNAME</code> or <code>BASIC_AUTH_PASSWORD</code> in the backend Vercel project’s Environment Variables, then redeploy it.</p></section></main>;
}
