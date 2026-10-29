import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useOutletContext } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../lib/auth";
import type { Provider } from "../types";

export interface HrContext {
  provider: string;
  providers: Provider[];
  company: string;
}

export const useHr = () => useOutletContext<HrContext>();

export function HrLayout() {
  const { user, signOut } = useAuth();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState("");
  const [company, setCompany] = useState("");

  useEffect(() => {
    api.providers().then((ps) => {
      setProviders(ps);
      setProvider((p) => p || ps.find((x) => x.is_default)?.name || "mock");
    });
    api.company().then((c) => setCompany(c.name));
  }, []);

  const current = providers.find((p) => p.name === provider);

  return (
    <div className="hr">
      <aside className="hr-side">
        <Link to="/hr" className="hr-brand">
          <span className="wordmark">{company || "Кабинет"}</span>
          <span className="muted small">кабинет HR</span>
        </Link>
        <nav className="hr-nav" aria-label="Разделы кабинета">
          <NavLink to="/hr" end>
            Отклики
          </NavLink>
          <NavLink to="/hr/vacancies">Вакансии</NavLink>
          <NavLink to="/hr/assistant">Ассистент</NavLink>
          <NavLink to="/hr/company">Страница компании</NavLink>
        </nav>
        <div className="hr-side-foot">
          <label className="field compact">
            <span>Модель ИИ</span>
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              {providers.map((p) => (
                <option key={p.name} value={p.name} disabled={!p.configured}>
                  {p.name === "mock" ? "без ИИ (эвристика)" : `${p.name}, ${p.default_model}`}
                  {p.configured ? "" : " — нет ключа"}
                </option>
              ))}
            </select>
          </label>
          {current?.name === "mock" && <p className="hint">Сейчас работает эвристика по ключевым словам. Для настоящего разбора добавьте ключ OpenAI или Gemini в .env.</p>}
          <div className="hr-user">
            <span>{user?.full_name}</span>
            <span className="row-gap">
              <Link to="/">На сайт</Link>
              <button className="link-btn" onClick={signOut}>
                Выйти
              </button>
            </span>
          </div>
        </div>
      </aside>
      <div className="hr-main">
        <Outlet context={{ provider, providers, company } satisfies HrContext} />
      </div>
    </div>
  );
}
