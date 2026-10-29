import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { STAGES, STAGE_FOR_HR, VERDICT } from "../lib/format";
import type { CandidateDetail, MatchStatus, Stage, Vacancy } from "../types";
import { useHr } from "./HrLayout";

type Tab = "profile" | "fit" | "questions" | "letter";

const STATUS_WORD: Record<MatchStatus, string> = { met: "есть", partial: "частично", missing: "не нашёл" };

export function ApplicantDetail() {
  const { id } = useParams();
  const cid = Number(id);
  const nav = useNavigate();
  const { provider } = useHr();
  const [d, setD] = useState<CandidateDetail | null>(null);
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("profile");
  const [view, setView] = useState<"file" | "text">("file");
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    const c = await api.candidate(cid);
    setD(c);
    return c;
  }, [cid]);

  useEffect(() => {
    let url: string | null = null;
    load().then(async (c) => {
      setVacancy(await api.vacancy(c.vacancy_id));
      url = await api.fileUrl(cid).catch(() => null);
      setFileUrl(url);
    });
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [cid, load]);

  useEffect(() => {
    if (d && (d.status === "uploaded" || d.status === "processing")) {
      const t = setTimeout(load, 1500);
      return () => clearTimeout(t);
    }
  }, [d, load]);

  if (!d) return <div className="hr-page muted">Открываю карточку…</div>;
  const s = d.screening;
  const p = s?.profile;
  const reqs = vacancy?.requirements ?? [];
  const byId = Object.fromEntries((s?.matches ?? []).map((m) => [m.requirement_id, m]));

  const setStage = async (stage: Stage) => {
    setD({ ...d, stage });
    await api.setStage(d.id, stage);
  };

  const act = async (fn: () => Promise<unknown>, done: string) => {
    try {
      await fn();
      setNote(done);
      load();
    } catch (e) {
      setNote(`Не получилось: ${(e as Error).message}`);
    }
  };

  const isPdf = d.file_mime === "application/pdf";

  return (
    <div className="hr-page detail">
      <header className="detail-head">
        <div>
          <Link to={`/hr/vacancies/${d.vacancy_id}`} className="back">
            {vacancy?.title ?? "К откликам"}
          </Link>
          <h1>{d.name || d.filename}</h1>
          <p className="muted">
            {[p?.headline, d.email, d.phone].filter(Boolean).join(", ") || d.filename}
            {d.source === "site" ? ". Отклик с сайта" : ""}
          </p>
        </div>
        <div className="stage-bar" role="radiogroup" aria-label="Этап отбора">
          {STAGES.map((st) => (
            <button key={st} role="radio" aria-checked={d.stage === st} className={`s-${st} ${d.stage === st ? "on" : ""}`} onClick={() => setStage(st)}>
              {STAGE_FOR_HR[st]}
            </button>
          ))}
        </div>
      </header>

      <div className="detail-grid">
        <section className="doc" aria-label="Резюме кандидата">
          {isPdf && fileUrl && (
            <div className="doc-switch" role="tablist" aria-label="Вид резюме">
              <button role="tab" aria-selected={view === "file"} className={view === "file" ? "on" : ""} onClick={() => setView("file")}>
                PDF
              </button>
              <button role="tab" aria-selected={view === "text"} className={view === "text" ? "on" : ""} onClick={() => setView("text")}>
                Текст, контакты скрыты
              </button>
            </div>
          )}
          {fileUrl && isPdf && view === "file" ? (
            <iframe src={fileUrl} title={`Резюме ${d.name}`} />
          ) : (
            <pre className="doc-text">{d.masked_text}</pre>
          )}
          {fileUrl && (
            <a href={fileUrl} download={d.filename} className="doc-download">
              Скачать оригинал
            </a>
          )}
        </section>

        <section className="ai" aria-label="Разбор ИИ">
          {!s ? (
            <p className="muted">{d.status === "failed" ? `Не удалось разобрать: ${d.error}` : "ИИ читает резюме…"}</p>
          ) : (
            <>
              <div className="ai-score">
                <span className={`big-score v-${d.verdict}`}>{Math.round(d.score ?? 0)}</span>
                <div>
                  <strong>{d.verdict ? VERDICT[d.verdict] : ""}</strong>
                  <p className="muted small">соответствие требованиям вакансии из 100</p>
                </div>
              </div>
              {s.summary && <p className="ai-summary">{s.summary}</p>}

              <div className="tabs-line" role="tablist">
                {(
                  [
                    ["profile", "Резюме"],
                    ["fit", "Требования"],
                    ["questions", "Вопросы"],
                    ["letter", "Письмо"],
                  ] as [Tab, string][]
                ).map(([k, label]) => (
                  <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? "on" : ""} onClick={() => setTab(k)} disabled={k === "letter" && !d.cover_letter}>
                    {label}
                  </button>
                ))}
              </div>

              {tab === "profile" && (
                <div className="ai-body">
                  {p?.experience?.length ? (
                    <ol className="timeline">
                      {p.experience.map((e, i) => (
                        <li key={i}>
                          <span className="tl-period">{e.period}</span>
                          <strong>{e.role}</strong>
                          {e.company && <span className="muted"> в {e.company}</span>}
                          {e.highlights.length > 0 && (
                            <ul>
                              {e.highlights.slice(0, 4).map((h, j) => (
                                <li key={j}>{h}</li>
                              ))}
                            </ul>
                          )}
                        </li>
                      ))}
                    </ol>
                  ) : (
                    <p className="muted">Места работы не выделились — посмотрите оригинал слева.</p>
                  )}
                  {p?.skills?.length ? (
                    <>
                      <h3>Навыки</h3>
                      <p className="skills">{p.skills.map((x) => <span key={x}>{x}</span>)}</p>
                    </>
                  ) : null}
                  {p?.education?.length ? (
                    <>
                      <h3>Образование</h3>
                      <ul className="plain">{p.education.map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </>
                  ) : null}
                  <div className="two">
                    <div>
                      <h3>Сильные стороны</h3>
                      <ul className="plain">{s.strengths.slice(0, 6).map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                    <div>
                      <h3>Что уточнить</h3>
                      <ul className="plain risks">{s.risks.length ? s.risks.slice(0, 6).map((x, i) => <li key={i}>{x}</li>) : <li className="muted">Явных рисков нет</li>}</ul>
                    </div>
                  </div>
                </div>
              )}

              {tab === "fit" && (
                <div className="ai-body">
                  {(["must", "nice"] as const).map((kind) => (
                    <div key={kind}>
                      <h3>{kind === "must" ? "Обязательные" : "Будет плюсом"}</h3>
                      <ul className="fit">
                        {reqs
                          .filter((r) => r.kind === kind)
                          .map((r) => {
                            const m = byId[r.id];
                            const st = (m?.status ?? "missing") as MatchStatus;
                            return (
                              <li key={r.id} className={`f-${st}`}>
                                <span className="fit-mark">{STATUS_WORD[st]}</span>
                                <div>
                                  <span>{r.text}</span>
                                  {m?.evidence && <q>{m.evidence}</q>}
                                </div>
                              </li>
                            );
                          })}
                      </ul>
                    </div>
                  ))}
                </div>
              )}

              {tab === "questions" && (
                <ol className="ai-body questions">
                  {s.interview_questions.map((q, i) => (
                    <li key={i}>{q}</li>
                  ))}
                </ol>
              )}

              {tab === "letter" && <p className="ai-body letter">{d.cover_letter}</p>}

              {d.usage && (
                <p className="usage">
                  {d.usage.provider === "mock" ? "Эвристика без ИИ" : `${d.usage.provider} · ${d.usage.model}`}, {d.usage.latency_ms} мс, ${d.usage.cost_usd.toFixed(4)}
                </p>
              )}
            </>
          )}

          <div className="ai-actions">
            <button className="btn btn-soft" onClick={() => act(() => api.rescreen(d.id, provider), "Перепроверяю выбранной моделью…")}>
              Перепроверить
            </button>
            <button className="btn btn-soft" onClick={() => act(() => api.exportTo(d.id, "bitrix24"), "Отправлено в Битрикс24 (тестовый режим — смотрите журнал интеграций)")}>
              В Битрикс24
            </button>
            <button className="btn btn-soft" onClick={() => act(() => api.exportTo(d.id, "1c"), "Отправлено в 1С (тестовый режим)")}>
              В 1С
            </button>
            <button
              className="btn btn-ghost danger"
              onClick={async () => {
                if (!window.confirm("Удалить кандидата вместе с резюме? Отменить нельзя.")) return;
                await api.removeCandidate(d.id);
                nav(`/hr/vacancies/${d.vacancy_id}`);
              }}
            >
              Удалить
            </button>
          </div>
          {note && <p className="note">{note}</p>}
        </section>
      </div>
    </div>
  );
}
