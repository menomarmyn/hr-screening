import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Provider, Vacancy } from "./types";
import { VacancyForm } from "./components/VacancyForm";
import { CandidatesView } from "./components/CandidatesView";
import { AgentChat } from "./components/AgentChat";
import { AnalyticsView } from "./components/AnalyticsView";
import { plural } from "./components/ui";

type Tab = "candidates" | "agent" | "analytics" | "requirements";

const TABS: [Tab, string][] = [
  ["candidates", "Кандидаты"],
  ["agent", "Ассистент"],
  ["analytics", "Аналитика"],
  ["requirements", "Требования"],
];

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
      setError("");
      setCurrent((c) => c ?? vs[0]?.id ?? null);
      if (vs.length === 0) setCreating(true);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const vacancy = vacancies.find((v) => v.id === current) ?? null;
  const active = providers.find((p) => p.name === provider);

  return (
    <div className="shell">
      <aside className="rail">
        <div className="wordmark">
          HR <span>Screener</span>
        </div>

        <nav aria-label="Вакансии">
          <h2 className="rail-title">Вакансии</h2>
          <ul className="vacancies">
            {vacancies.map((v) => (
              <li key={v.id}>
                <button
                  className={`vacancy ${v.id === current && !creating ? "is-active" : ""}`}
                  onClick={() => {
                    setCurrent(v.id);
                    setCreating(false);
                  }}
                >
                  <span className="vacancy-title">{v.title}</span>
                  <span className="vacancy-meta">
                    {v.company || "Без компании"}, {v.candidates_count} {plural(v.candidates_count, "кандидат", "кандидата", "кандидатов")}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button className="btn quiet full" onClick={() => setCreating(true)}>
            Добавить вакансию
          </button>
        </nav>

        <div className="rail-model">
          <label htmlFor="model" className="rail-title">
            Модель для оценки
          </label>
          <select id="model" className="select" value={provider} onChange={(e) => setProvider(e.target.value)}>
            {providers.map((p) => (
              <option key={p.name} value={p.name} disabled={!p.configured}>
                {p.name}: {p.default_model}
                {p.configured ? "" : " (нужен ключ)"}
              </option>
            ))}
          </select>
          <p className="muted small">
            {active?.name === "mock" ? "Эвристика по ключевым словам, без API-ключей. Для LLM добавьте ключ в файл .env." : "Новые и перепроверенные резюме оценит эта модель."}
          </p>
        </div>
      </aside>

      <main className="main">
        {error && <div className="alert">API не отвечает ({error}). Проверьте, что запущено окно «HR Screener API».</div>}
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
            <header className="masthead">
              <p className="company">{vacancy.company || "Вакансия"}</p>
              <h1>{vacancy.title}</h1>
              <div className="tabs" role="tablist">
                {TABS.map(([id, label]) => (
                  <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? "is-active" : ""}`} onClick={() => setTab(id)}>
                    {label}
                    {id === "requirements" && <span className="tab-count">{vacancy.requirements.length}</span>}
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
    <div className="req-page">
      <p className="lead">Требования выделены из текста вакансии. Обязательные весят в итоговом балле вдвое больше, чем «плюсом». Если у кандидата нет больше половины обязательных, вердикт — отказ.</p>
      {(["must", "nice"] as const).map((kind) => {
        const list = vacancy.requirements.filter((r) => r.kind === kind);
        return (
          <section key={kind} className="req-block">
            <h2>
              {kind === "must" ? "Обязательные" : "Будет плюсом"} <span className="muted">{list.length}</span>
            </h2>
            <ol className="req-list" start={kind === "must" ? 1 : vacancy.requirements.filter((r) => r.kind === "must").length + 1}>
              {list.map((r) => (
                <li key={r.id}>
                  <span>{r.text}</span>
                  {r.category !== "soft" && <span className="tag">{r.category}</span>}
                </li>
              ))}
            </ol>
          </section>
        );
      })}
    </div>
  );
}
