import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Candidate, CandidateDetail, Vacancy } from "../types";
import { ScoreBadge, VerdictPill } from "./ui";

export function CandidatesView({ vacancy, provider, onChange }: { vacancy: Vacancy; provider: string; onChange: () => void }) {
  const [items, setItems] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const list = await api.candidates(vacancy.id);
    setItems(list);
    return list;
  }, [vacancy.id]);

  useEffect(() => {
    setSelected(null);
    load();
  }, [load]);

  // Пока есть кандидаты в обработке — опрашиваем API (скрининг идёт в фоне через Celery)
  useEffect(() => {
    if (!items.some((c) => c.status === "uploaded" || c.status === "processing")) return;
    const t = setTimeout(load, 1500);
    return () => clearTimeout(t);
  }, [items, load]);

  const upload = async (files: File[]) => {
    if (!files.length) return;
    setUploading(true);
    setError("");
    try {
      await api.upload(vacancy.id, files, provider);
      await load();
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="split">
      <section className="card">
        <div
          className={`dropzone ${drag ? "drag" : ""}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            upload(Array.from(e.dataTransfer.files));
          }}
        >
          <input ref={input} type="file" multiple accept=".pdf,.docx,.txt,.md" hidden onChange={(e) => upload(Array.from(e.target.files ?? []))} />
          <strong>{uploading ? "Загружаю…" : "Перетащите резюме сюда"}</strong>
          <span className="muted">PDF, DOCX или TXT · можно несколько файлов · модель: {provider}</span>
        </div>
        {error && <div className="alert">{error}</div>}

        {items.length === 0 ? (
          <p className="empty">Кандидатов пока нет. Примеры резюме лежат в папке data/resumes.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Кандидат</th>
                <th>Балл</th>
                <th>Вердикт</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c, i) => (
                <tr key={c.id} className={c.id === selected ? "selected" : ""} onClick={() => setSelected(c.id)}>
                  <td className="mono muted">{i + 1}</td>
                  <td>
                    <div className="cand-name">{c.name || c.filename}</div>
                    <div className="muted small">
                      #{c.id} · {c.filename}
                      {c.crm_id && <span className="chip ok">в CRM</span>}
                    </div>
                  </td>
                  <td>
                    {c.status === "screened" ? (
                      <ScoreBadge score={c.score!} />
                    ) : c.status === "failed" ? (
                      <span className="chip bad" title={c.error}>
                        ошибка
                      </span>
                    ) : (
                      <span className="spinner" />
                    )}
                  </td>
                  <td>{c.verdict && <VerdictPill verdict={c.verdict} />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card detail">
        {selected ? (
          <CandidatePanel
            key={selected}
            id={selected}
            vacancy={vacancy}
            provider={provider}
            onChanged={async () => {
              await load();
              onChange();
            }}
            onDeleted={async () => {
              setSelected(null);
              await load();
              onChange();
            }}
          />
        ) : (
          <p className="empty">Выберите кандидата, чтобы увидеть разбор по требованиям.</p>
        )}
      </section>
    </div>
  );
}

function CandidatePanel({
  id,
  vacancy,
  provider,
  onChanged,
  onDeleted,
}: {
  id: number;
  vacancy: Vacancy;
  provider: string;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const [d, setD] = useState<CandidateDetail | null>(null);
  const [showResume, setShowResume] = useState(false);
  const [note, setNote] = useState("");

  const load = useCallback(() => api.candidate(id).then(setD), [id]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (d && (d.status === "uploaded" || d.status === "processing")) {
      const t = setTimeout(load, 1500);
      return () => clearTimeout(t);
    }
  }, [d, load]);

  if (!d) return <span className="spinner" />;
  const s = d.screening;
  const reqById = Object.fromEntries(vacancy.requirements.map((r) => [r.id, r]));

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    try {
      await fn();
      setNote(msg);
      await load();
      onChanged();
    } catch (e) {
      setNote((e as Error).message);
    }
  };

  return (
    <div>
      <div className="detail-head">
        <div>
          <h2>{d.name || d.filename}</h2>
          <div className="muted small">
            {s?.seniority !== "unknown" && s?.seniority} {s?.years_of_experience != null && `· ${s.years_of_experience} лет опыта`}
          </div>
        </div>
        {d.score != null && <ScoreBadge score={d.score} large />}
      </div>

      <div className="actions wrap">
        <button className="btn" onClick={() => act(() => api.exportTo(id, "bitrix24"), "Отправлено в Битрикс24 (см. журнал интеграций)")}>
          → Битрикс24
        </button>
        <button className="btn" onClick={() => act(() => api.exportTo(id, "1c"), "Отправлено в 1С (см. журнал интеграций)")}>
          → 1С
        </button>
        <button className="btn ghost" onClick={() => act(() => api.rescreen(id, provider), `Повторный скрининг: ${provider}`)}>
          Перепроверить ({provider})
        </button>
        <button
          className="btn ghost danger"
          onClick={async () => {
            if (window.confirm("Удалить кандидата и все его данные?")) {
              await api.remove(id);
              onDeleted();
            }
          }}
        >
          Удалить ПДн
        </button>
      </div>
      {note && <div className="note">{note}</div>}

      {d.status === "failed" && <div className="alert">Ошибка скрининга: {d.error}</div>}
      {!s ? (
        <p className="muted">Идёт скрининг…</p>
      ) : (
        <>
          {s.summary && <p className="summary">{s.summary}</p>}

          <div className="two-col">
            <div>
              <h4>Сильные стороны</h4>
              <ul className="bullets">{s.strengths.map((x, i) => <li key={i}>{x}</li>)}</ul>
            </div>
            <div>
              <h4>Риски</h4>
              <ul className="bullets risk">{s.risks.length ? s.risks.map((x, i) => <li key={i}>{x}</li>) : <li>Не выявлено</li>}</ul>
            </div>
          </div>

          <h4>Соответствие требованиям</h4>
          <ul className="matrix">
            {s.matches.map((m) => {
              const r = reqById[m.requirement_id];
              return (
                <li key={m.requirement_id} className={`m-${m.status}`}>
                  <span className="dot" title={m.status} />
                  <div>
                    <div>
                      {r?.text ?? m.requirement_id} {r?.kind === "nice" && <span className="chip">плюс</span>}
                    </div>
                    {m.evidence && <div className="evidence">«{m.evidence}»</div>}
                    {!m.evidence && m.comment && <div className="muted small">{m.comment}</div>}
                  </div>
                </li>
              );
            })}
          </ul>

          <h4>Вопросы для интервью</h4>
          <ol className="questions">{s.interview_questions.map((q, i) => <li key={i}>{q}</li>)}</ol>

          {d.usage && (
            <div className="usage mono">
              {d.usage.provider}/{d.usage.model} · {d.usage.input_tokens + d.usage.output_tokens} токенов · ${d.usage.cost_usd.toFixed(5)} ·{" "}
              {d.usage.latency_ms} мс
            </div>
          )}
        </>
      )}

      <button className="link" onClick={() => setShowResume((x) => !x)}>
        {showResume ? "Скрыть резюме" : "Показать резюме (контакты скрыты)"}
      </button>
      {showResume && <pre className="resume">{d.masked_text}</pre>}
    </div>
  );
}
