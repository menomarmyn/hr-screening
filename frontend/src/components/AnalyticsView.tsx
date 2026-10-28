import { useEffect, useState } from "react";
import { api } from "../api";
import type { Analytics, Candidate, MatchStatus, Vacancy } from "../types";
import { Score, Spinner } from "./ui";

export function AnalyticsView({ vacancy }: { vacancy: Vacancy }) {
  const [a, setA] = useState<Analytics | null>(null);
  const [rows, setRows] = useState<Candidate[]>([]);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    api.analytics(vacancy.id).then(setA);
    api.candidates(vacancy.id).then(async (list) => {
      // для совместимости со старым API собираем статусы из карточек
      const full = await Promise.all(
        list
          .filter((c) => c.status === "screened")
          .map(async (c) => {
            if (c.fingerprint?.length) return c;
            const d = await api.candidate(c.id);
            const by = Object.fromEntries((d.screening?.matches ?? []).map((m) => [m.requirement_id, m.status]));
            return { ...c, fingerprint: vacancy.requirements.map((r) => (by[r.id] ?? "missing") as MatchStatus) };
          }),
      );
      setRows(full);
    });
  }, [vacancy]);

  if (!a) return <Spinner label="Считаю аналитику" />;

  const reqs = vacancy.requirements;
  const coverage = reqs.map((_, j) => rows.filter((c) => c.fingerprint?.[j] === "met").length);
  const scarce = reqs
    .map((r, j) => ({ r, met: coverage[j] }))
    .filter((x) => x.r.kind === "must" && x.r.category !== "soft") // soft skills по резюме не проверить
    .sort((x, y) => x.met - y.met)
    .slice(0, 5);
  const hovered = hover != null ? reqs[hover] : null;

  return (
    <div className="analytics">
      <p className="summary-line">
        В воронке <strong>{a.candidates}</strong> кандидатов: пригласить <strong className="t-strong">{a.verdicts.strong ?? 0}</strong>, рассмотреть{" "}
        <strong className="t-maybe">{a.verdicts.maybe ?? 0}</strong>, отказ <strong className="t-reject">{a.verdicts.reject ?? 0}</strong>. Средний балл{" "}
        <strong>{a.avg_score ?? "—"}</strong>.
      </p>

      <section className="heat-wrap">
        <div className="heat-head">
          <h3>Карта соответствия</h3>
          <p className="muted small heat-hint">{hovered ? `${hovered.kind === "must" ? "Обязательное" : "Плюсом"}: ${hovered.text}` : "Наведите на столбец, чтобы увидеть требование"}</p>
        </div>
        <div className="heat-scroll">
          <table className="heat" onMouseLeave={() => setHover(null)}>
            <thead>
              <tr>
                <th className="heat-name" />
                {reqs.map((r, j) => (
                  <th key={r.id} className={`${r.kind === "nice" && reqs[j - 1]?.kind === "must" ? "gap" : ""} ${hover === j ? "is-hover" : ""}`} onMouseEnter={() => setHover(j)} title={r.text}>
                    {j + 1}
                  </th>
                ))}
                <th className="heat-score">Балл</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <th className="heat-name" scope="row">
                    {c.name || c.filename}
                  </th>
                  {reqs.map((r, j) => (
                    <td
                      key={r.id}
                      className={`s-${c.fingerprint?.[j] ?? "missing"} ${r.kind === "nice" && reqs[j - 1]?.kind === "must" ? "gap" : ""} ${hover === j ? "is-hover" : ""}`}
                      onMouseEnter={() => setHover(j)}
                      title={`${c.name}: ${r.text}`}
                    />
                  ))}
                  <td className="heat-score">{c.score != null && <Score score={c.score} verdict={c.verdict} />}</td>
                </tr>
              ))}
              <tr className="heat-total">
                <th className="heat-name" scope="row">
                  Подтвердили
                </th>
                {coverage.map((n, j) => (
                  <td key={j} className={`${reqs[j].kind === "nice" && reqs[j - 1]?.kind === "must" ? "gap" : ""} ${hover === j ? "is-hover" : ""}`} onMouseEnter={() => setHover(j)}>
                    {n}
                  </td>
                ))}
                <td />
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div className="analytics-cols">
        <section>
          <h3>Реже всего подтверждают</h3>
          <p className="muted small">Обязательные технические требования, которые подтверждает меньшинство. Возможно, их стоит перевести в «плюсом». Soft skills сюда не входят — их проверяют на интервью.</p>
          <ul className="scarce">
            {scarce.map(({ r, met }) => (
              <li key={r.id}>
                <span>{r.text}</span>
                <span className="scarce-n">
                  {met} из {rows.length}
                </span>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <h3>Стоимость скрининга</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Модель</th>
                <th>Резюме</th>
                <th>Всего, $</th>
                <th>Время ответа</th>
              </tr>
            </thead>
            <tbody>
              {a.cost.by_model.map((m) => (
                <tr key={m.model}>
                  <td>{m.model}</td>
                  <td>{m.count}</td>
                  <td>{m.cost_usd.toFixed(4)}</td>
                  <td>{m.avg_latency_ms} мс</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted small">
            Одно резюме обходится в ${a.cost.per_resume_usd.toFixed(4)}, всего потрачено {a.cost.tokens.toLocaleString("ru-RU")} токенов.
          </p>
          <h3>Навыки в воронке</h3>
          <p className="skills">
            {a.top_skills.map(([skill, n]) => (
              <span key={skill} className="skill">
                {skill} <b>{n}</b>
              </span>
            ))}
          </p>
        </section>
      </div>
    </div>
  );
}
