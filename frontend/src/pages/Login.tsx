import { useState, type FormEvent } from "react";
import { ArrowRight, CircleHelp } from "lucide-react";
import { api, type User } from "../api";
import { Logo, Field, ErrorBox, message } from "../ui";

export default function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(f)),
      });
      onLogin(await api<User>("/me"));
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-card">
        <Logo />
        <h1>Sign in to your workspace</h1>
        <p>Keep orders moving and payment records in order.</p>
        <form onSubmit={submit}>
          <Field label="Email">
            <input
              name="email"
              type="email"
              autoComplete="username"
              required
              autoFocus
            />
          </Field>
          <Field label="Password">
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={128}
            />
          </Field>
          <ErrorBox text={error} />
          <button className="button primary" disabled={busy}>
            {busy ? "Signing in..." : "Sign in"}
            <ArrowRight size={16} />
          </button>
        </form>
        <div className="login-note">
          <CircleHelp size={16} />
          <span>Ask your workspace administrator for access.</span>
        </div>
      </section>
      <p className="login-footer">BridgeSync / Business operations</p>
    </main>
  );
}
