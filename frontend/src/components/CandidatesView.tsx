import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Candidate, CandidateDetail, MatchStatus, Vacancy } from "../types";
import { Fingerprint, Score, Spinner, StatusDot, VerdictTag, plural } from "./ui";

/** Старый API может не отдавать fingerprint — тогда собираем его из деталей кандидата. */
async function withFingerprints(list: Candidate[], vacancy: Vacancy): Promise<Candidate[]> {
  return Promise.all(
    list.map(async (c) => {
      if (c.status !== "screened" || (c.fingerprint && c.fingerprint.length)) return c;
      const d = await api.candidate(c.id);
      const by = Object.fromEntries((d.screening?.matches ?? []).map((m) => [m.requirement_id, m.status]));
      return { ...c, fingerprint: vacancy.requirements.map((r) => (by[r.id] ?? "missing") as MatchStatus) };
    }),
  );
}

export function CandidatesView({ vacancy, provider, onChange }: { vacancy: Vacancy; provider: string; onChange: () => void }) {
  const [items, setItems] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const list = await withFingerprints(await api.candidates(vacancy.id), vacancy);
    setItems(list);
    setSelected((s) => s ?? list[0]?.id ?? null);
    return list;
  }, [vacancy]);

  useEffect(() => {
    setSelected(null);
    load();
  }, [load]);

  // Скрининг идёт в фоне — пока есть необработанные, опрашиваем API
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

  const mustCount = vacancy.requirements.filter((r) => r.kind === "must").length;

  return (
    <div className="board">
      <section className="roster" aria-label="Рейтинг кандидатов">
        <div
          className={`drop ${drag ? "is-drag" : ""}`}
          onClick={() => input.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
          role="button"
          tabIndex={0}
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
          <span className="drop-plus" aria-hidden>
            +
          </span>
          <span>
            <strong>{uploading ? "Загружаю резюме…" : "Добавить резюме"}</strong>
            <span className="muted"> — перетащите PDF, DOCX или TXT, можно сразу пачкой</span>
          </span>
        </div>
        {error && <div className="alert">{error}</div>}

        {items.length > 0 && (
          <div className="legend" aria-hidden>
            <span>
              Каждая полоса — {vacancy.requirements.length} {plural(vacancy.requirements.length, "требование", "требования", "требований")}: сначала {mustCount} обязательных, затем «плюсом»
            </span>
            <span className="legend-keys">
              <span>
                <i className="fp-cell s-met" /> есть
              </span>
              <span>
                <i className="fp-cell s-partial" /> частично
              </span>
              <span>
                <i className="fp-cell s-missing" /> нет
              </span>
            </span>
          </div>
        )}

        {items.length === 0 ? (
          <div className="empty">
            <p>Здесь появится рейтинг. Загрузите первые резюме — скрининг займёт несколько секунд на каждое.</p>
          </div>
        ) : (
          <ol className="rows">
            {items.map((c, i) => (
              <li key={c.id}>
                <button className={`row ${c.id === selected ? "is-active" : ""} ${c.verdict === "reject" ? "is-dim" : ""}`} onClick={() => setSelected(c.id)}>
                  <span className="row-rank">{i + 1}</span>
                  <span className="row-who">
                    <span className="row-name">{c.name || c.filename}</span>
                    <span className="row-meta">
                      {c.verdict ? <VerdictTag verdict={c.verdict} /> : <span className="muted">{c.status === "failed" ? "ошибка обработки" : "в обработке"}</span>}
                      {c.crm_id && <span className="tag">в CRM</span>}
                    </span>
                  </span>
                  <Fingerprint statuses={c.fingerprint ?? []} requirements={vacancy.requirements} />
                  <span className="row-score">{c.status === "screened" ? <Score score={c.score!} verdict={c.verdict} /> : c.status === "failed" ? "—" : <Spinner />}</span>
                </button>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="dossier" aria-label="Карточка кандидата">
        {selected ? (
          <Dossier
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
          <div className="empty">
            <p>Выберите кандидата слева, чтобы открыть разбор по требованиям.</p>
          </div>
        )}
      </section>
    </div>
  );
}

function Dossier({
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
  const [openReq, setOpenReq] = useState<string | null>(null);

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

  if (!d) return <Spinner label="Открываю карточку" />;
  const s = d.screening;

  const act = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn();
      setNote(done);
      await load();
      onChanged();
    } catch (e) {
      setNote(`Не получилось: ${(e as Error).message}`);
    }
  };

  const matchBy = Object.fromEntries((s?.matches ?? []).map((m) => [m.requirement_id, m]));
  const statuses = vacancy.requirements.map((r) => (matchBy[r.id]?.status ?? "missing") as MatchStatus);
  const met = statuses.filter((x) => x === "met").length;
  const experience = [s?.seniority && s.seniority !== "unknown" ? s.seniority : null, s?.years_of_experience != null ? `${s.years_of_experience} лет опыта` : null]
    .filter(Boolean)
    .join(", ");

  return (
    <article>
      <header className="dossier-head">
        <div>
          <h2>{d.name || d.filename}</h2>
          <p className="muted">
            {experience || "Опыт не указан"}. Файл {d.filename}
          </p>
        </div>
        {d.score != null && (
          <div className="dossier-score">
            <Score score={d.score} verdict={d.verdict} size="xl" />
            {d.verdict && <VerdictTag verdict={d.verdict} />}
          </div>
        )}
      </header>

      {s && (
        <div className="dossier-print">
          <Fingerprint statuses={statuses} requirements={vacancy.requirements} size="lg" />
          <span className="muted">
            Подтверждено {met} из {statuses.length}
          </span>
        </div>
      )}

      <div className="actions">
        <button className="btn primary" onClick={() => act(() => api.exportTo(id, "bitrix24"), "Кандидат отправлен в Битрикс24. Запрос записан в журнал интеграций.")}>
          Отправить в Битрикс24
        </button>
        <button className="btn" onClick={() => act(() => api.exportTo(id, "1c"), "Кандидат отправлен в 1С. Запрос записан в журнал интеграций.")}>
          Отправить в 1С
        </button>
        <button className="btn quiet" onClick={() => act(() => api.rescreen(id, provider), `Перепроверяю моделью ${provider}`)}>
          Перепроверить
        </button>
        <button
          className="btn quiet danger"
          onClick={async () => {
            if (window.confirm("Удалить кандидата вместе с резюме и контактами? Это действие нельзя отменить.")) {
              await api.remove(id);
              onDeleted();
            }
          }}
        >
          Удалить данные
        </button>
      </div>
      {note && (
        <p className="note" role="status">
          {note}
        </p>
      )}

      {d.status === "failed" && <div className="alert">Скрининг не прошёл: {d.error}. Нажмите «Перепроверить» или выберите другую модель.</div>}

      {!s ? (
        <Spinner label="Идёт скрининг" />
      ) : (
        <>
          {s.summary && <p className="lead">{s.summary}</p>}

          <div className="pros-cons">
            <div>
              <h3>Сильные стороны</h3>
              <ul>{s.strengths.length ? s.strengths.map((x, i) => <li key={i}>{x}</li>) : <li className="muted">Не выделены</li>}</ul>
            </div>
            <div>
              <h3>Что проверить</h3>
              <ul className="risks">{s.risks.length ? s.risks.map((x, i) => <li key={i}>{x}</li>) : <li className="muted">Явных рисков нет</li>}</ul>
            </div>
          </div>

          {(["must", "nice"] as const).map((kind) => (
            <section key={kind} className="reqs">
              <h3>{kind === "must" ? "Обязательные требования" : "Будет плюсом"}</h3>
              <ul>
                {vacancy.requirements
                  .filter((r) => r.kind === kind)
                  .map((r) => {
                    const m = matchBy[r.id];
                    const status = (m?.status ?? "missing") as MatchStatus;
                    const detail = m?.evidence || m?.comment;
                    const open = openReq === r.id;
                    return (
                      <li key={r.id} className={`req s-${status}`}>
                        <button className="req-line" onClick={() => setOpenReq(open ? null : r.id)} aria-expanded={open} disabled={!detail}>
                          <StatusDot status={status} />
                          <span>{r.text}</span>
                        </button>
                        {open && detail && <p className={m?.evidence ? "evidence" : "muted small"}>{m?.evidence ? `«${m.evidence}»` : detail}</p>}
                      </li>
                    );
                  })}
              </ul>
            </section>
          ))}

          <section className="questions">
            <h3>Вопросы для интервью</h3>
            <ol>
              {s.interview_questions.map((q, i) => (
                <li key={i}>{q}</li>
              ))}
            </ol>
          </section>

          {d.usage && (
            <p className="usage">
              Оценила модель {d.usage.provider}/{d.usage.model}: {d.usage.input_tokens + d.usage.output_tokens} токенов, ${d.usage.cost_usd.toFixed(5)}, {d.usage.latency_ms} мс
            </p>
          )}
        </>
      )}

      <button className="link" onClick={() => setShowResume((x) => !x)} aria-expanded={showResume}>
        {showResume ? "Скрыть резюме" : "Показать резюме — контакты скрыты"}
      </button>
      {showResume && <pre className="resume">{d.masked_text}</pre>}
    </article>
  );
}
