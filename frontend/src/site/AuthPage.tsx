import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { useAuth } from "../lib/auth";

const DEMO = import.meta.env.VITE_DEMO === "true";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const [params] = useSearchParams();
  const next = params.get("next");
  const nav = useNavigate();
  const { signIn } = useAuth();
  const [role, setRole] = useState<"candidate" | "hr">(params.get("role") === "hr" ? "hr" : "candidate");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invite, setInvite] = useState("");
  const [peek, setPeek] = useState(false);
  const [hidden, setHidden] = useState(false); // глаз закрывается, пока вводят пароль
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = mode === "login" ? await api.login(email, password) : await api.register({ email, password, full_name: name, role, invite_code: invite });
      signIn(r.token, r.user);
      nav(next && next.startsWith("/") ? next : r.user.role === "hr" ? "/hr" : "/me", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const demoLogin = async (who: "hr" | "candidate") => {
    setBusy(true);
    setError("");
    try {
      const r = await api.login(who === "hr" ? "hr@koz.demo" : "candidate@koz.demo", "koz-demo-2026");
      signIn(r.token, r.user);
      nav(r.user.role === "hr" ? "/hr" : "/me", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const q = next ? `?next=${encodeURIComponent(next)}` : "";

  return (
    <div className="page auth">
      <div className="auth-art" aria-hidden>
        <Eye size={220} mood={hidden && !peek ? "sleepy" : "open"} track={!hidden} />
        <p className="auth-art-note">{hidden && !peek ? "Не подглядываю." : mode === "login" ? "С возвращением." : "Рады знакомству."}</p>
      </div>
      <form className="auth-card" onSubmit={submit}>
        <h1>{mode === "login" ? "Вход" : "Создать аккаунт"}</h1>

        {mode === "register" && (
          <div className="segmented" role="radiogroup" aria-label="Тип аккаунта">
            <button type="button" role="radio" aria-checked={role === "candidate"} className={role === "candidate" ? "on" : ""} onClick={() => setRole("candidate")}>
              Ищу работу
            </button>
            <button type="button" role="radio" aria-checked={role === "hr"} className={role === "hr" ? "on" : ""} onClick={() => setRole("hr")}>
              Я из HR
            </button>
          </div>
        )}

        {mode === "register" && (
          <label className="field">
            <span>Имя и фамилия</span>
            <input value={name} onChange={(e) => setName(e.target.value)} required minLength={2} autoComplete="name" />
          </label>
        )}
        <label className="field">
          <span>Email</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </label>
        <label className="field">
          <span>Пароль</span>
          <span className="password">
            <input
              type={peek ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onFocus={() => setHidden(true)}
              onBlur={() => setHidden(false)}
              required
              minLength={mode === "register" ? 8 : 1}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
            <button type="button" className="peek" onClick={() => setPeek((x) => !x)} aria-pressed={peek}>
              {peek ? "Скрыть" : "Показать"}
            </button>
          </span>
          {mode === "register" && <small className="muted">Не меньше 8 символов</small>}
        </label>
        {mode === "register" && role === "hr" && (
          <label className="field">
            <span>Код приглашения</span>
            <input value={invite} onChange={(e) => setInvite(e.target.value)} required />
            <small className="muted">HR-аккаунты создаются по коду от администратора — так посторонние не увидят резюме кандидатов.</small>
          </label>
        )}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Секунду…" : mode === "login" ? "Войти" : "Создать аккаунт"}
        </button>
        {DEMO && mode === "login" && (
          <div className="demo-box">
            <p>
              <b>Демо-стенд.</b> Войдите в готовый аккаунт, чтобы посмотреть обе стороны сервиса.
            </p>
            <div className="demo-actions">
              <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => demoLogin("hr")}>
                Кабинет HR
              </button>
              <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => demoLogin("candidate")}>
                Кабинет кандидата
              </button>
            </div>
          </div>
        )}
        <p className="auth-switch">
          {mode === "login" ? (
            <>
              Нет аккаунта? <Link to={`/register${q}`}>Создайте</Link>
            </>
          ) : (
            <>
              Уже есть аккаунт? <Link to={`/login${q}`}>Войдите</Link>
            </>
          )}
        </p>
      </form>
    </div>
  );
}
