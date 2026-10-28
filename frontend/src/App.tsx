import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Provider, Vacancy } from "./types";
import { VacancyForm } from "./components/VacancyForm";
import { CandidatesView } from "./components/CandidatesView";
import { AgentChat } from "./components/AgentChat";
import { AnalyticsView } from "./components/AnalyticsView";

type Tab = "candidates" | "agent" | "analytics" | "requirements";

export default function App() {
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [current, setCurrent] = useState<number | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState("mock");
  const [tab, setTab] = useState<Tab>("candidates");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [vs, ps] = await Promise.all([api.vacancies(), api.providers()]);
      setVacancies(vs);
      setProviders(ps);
      setCurrent((c) => c ?? vs[0]?.id ?? null);
      if (vs.length === 0) setCreating(true);
    } catch (e) {
      setError(String((e as Error).message));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const vacancy = vacancies.find((v) => v.id === current) ?? null;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">HR</span>
          <div>
            <div className="brand-title">Screener</div>
            <div className="brand-sub">AI-скрининг резюме</div>
          </div>
        </div>

        <div className="side-label">Вакансии</div>
        <nav className="vacancy-list">
          {vacancies.map((v) => (
            <button
              key={v.id}
              className={`vacancy-item ${v.id === current && !creating ? "active" : ""}`}
              onClick={() => {
                setCurrent(v.id);
                setCreating(false);
              }}
            >
              <span className="vacancy-title">{v.title}</span>
              <span className="vacancy-meta">
                {v.company || "—"} · {v.candidates_count} канд.
              </span>
            </button>
          ))}
        </nav>
        <button className="btn ghost full" onClick={() => setCreating(true)}>
          + Новая вакансия
        </button>

        <div className="side-label">Модель</div>
        <select className="select" value={provider} onChange={(e) => setProvider(e.target.value)}>
          {providers.map((p) => (
            <option key={p.name} value={p.name} disabled={!p.configured}>
              {p.name} — {p.default_model}
              {p.configured ? "" : " (нет ключа)"}
            </option>
          ))}
        </select>
        <p className="hint">mock — эвристика без API-ключей. Для LLM задайте ключ в .env.</p>
      </aside>

      <main className="main">
        {error && <div className="alert">Нет связи с API: {error}</div>}
        {creating ? (
          <VacancyForm
            onCreated={async (v) => {
              setCreating(false);
              await load();
              setCurrent(v.id);
              setTab("requirements");
            }}
            onCancel={vacancies.length ? () => setCreating(false) : undefined}
          />
        ) : vacancy ? (
          <>
            <header className="page-head">
              <div>
                <div className="eyebrow">{vacancy.company || "Вакансия"}</div>
                <h1>{vacancy.title}</h1>
              </div>
              <div className="tabs">
                {(
                  [
                    ["candidates", "Кандидаты"],
                    ["agent", "Ассистент"],
                    ["analytics", "Аналитика"],
                    ["requirements", `Требования · ${vacancy.requirements.length}`],
                  ] as [Tab, string][]
                ).map(([id, label]) => (
                  <button key={id} className={`tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
                    {label}
                  </button>
                ))}
              </div>
            </header>
            {tab === "candidates" && <CandidatesView vacancy={vacancy} provider={provider} onChange={load} />}
            {tab === "agent" && <AgentChat key={vacancy.id} vacancy={vacancy} provider={provider} />}
            {tab === "analytics" && <AnalyticsView vacancy={vacancy} />}
            {tab === "requirements" && <RequirementsList vacancy={vacancy} />}
          </>
        ) : null}
      </main>
    </div>
  );
}

function RequirementsList({ vacancy }: { vacancy: Vacancy }) {
  return (
    <section className="card">
      <p className="muted">Требования извлечены из текста вакансии. Обязательные весят ×2 в итоговом балле.</p>
      {(["must", "nice"] as const).map((kind) => (
        <div key={kind} className="req-group">
          <h3>{kind === "must" ? "Обязательные" : "Будет преимуществом"}</h3>
          <ul className="req-list">
            {vacancy.requirements
              .filter((r) => r.kind === kind)
              .map((r) => (
                <li key={r.id}>
                  <span className="mono muted">{r.id}</span>
                  <span>{r.text}</span>
                  <span className="chip">{r.category}</span>
                </li>
              ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
