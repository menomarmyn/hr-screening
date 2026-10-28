import { useEffect, useState } from "react";
import { api } from "../api";
import type { Analytics, Vacancy } from "../types";

export function AnalyticsView({ vacancy }: { vacancy: Vacancy }) {
  const [a, setA] = useState<Analytics | null>(null);
  useEffect(() => {
    api.analytics(vacancy.id).then(setA);
  }, [vacancy.id]);
  if (!a) return <span className="spinner" />;

  const maxSkill = Math.max(1, ...a.top_skills.map(([, n]) => n));
  const reqs = [...a.requirements].sort((x, y) => x.met / (a.screened || 1) - y.met / (a.screened || 1));

  return (
    <div className="analytics">
      <div className="kpis">
        <Kpi label="Кандидатов" value={a.candidates} />
        <Kpi label="Пригласить" value={a.verdicts.strong ?? 0} tone="hi" />
        <Kpi label="Рассмотреть" value={a.verdicts.maybe ?? 0} tone="mid" />
        <Kpi label="Средний балл" value={a.avg_score ?? "—"} />
        <Kpi label="Стоимость / резюме" value={`$${a.cost.per_resume_usd.toFixed(4)}`} />
        <Kpi label="Задержка" value={`${a.cost.avg_latency_ms} мс`} />
      </div>

      <div className="split">
        <section className="card">
          <h3>Дефицитные требования</h3>
          <p className="muted small">Доля кандидатов, у которых требование подтверждено. Помогает понять, не завышены ли ожидания в вакансии.</p>
          <ul className="bars">
            {reqs.slice(0, 12).map((r) => {
              const n = r.met + r.partial + r.missing || 1;
              return (
                <li key={r.text}>
                  <span className="bar-label" title={r.text}>
                    {r.kind === "must" ? "● " : "○ "}
                    {r.text}
                  </span>
                  <span className="stack">
                    <span className="seg met" style={{ width: `${(100 * r.met) / n}%` }} />
                    <span className="seg partial" style={{ width: `${(100 * r.partial) / n}%` }} />
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
        <section className="card">
          <h3>Навыки в воронке</h3>
          <ul className="bars">
            {a.top_skills.map(([skill, n]) => (
              <li key={skill}>
                <span className="bar-label">{skill}</span>
                <span className="stack">
                  <span className="seg met" style={{ width: `${(100 * n) / maxSkill}%` }} />
                </span>
                <span className="mono small">{n}</span>
              </li>
            ))}
          </ul>
          <h3>Модели</h3>
          <table className="table compact">
            <thead>
              <tr>
                <th>Модель</th>
                <th>Резюме</th>
                <th>$</th>
                <th>мс</th>
              </tr>
            </thead>
            <tbody>
              {a.cost.by_model.map((m) => (
                <tr key={m.model}>
                  <td className="mono">{m.model}</td>
                  <td>{m.count}</td>
                  <td>{m.cost_usd.toFixed(4)}</td>
                  <td>{m.avg_latency_ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string | number; tone?: string }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}
