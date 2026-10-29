import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconUpload } from "../illustrations/Icons";
import { STAGES, STAGE_FOR_HR, VERDICT, date, plural } from "../lib/format";
import type { Candidate, Stage, Vacancy } from "../types";
import { useHr } from "./HrLayout";

type Row = Candidate & { vacancy_title: string };

export function Applicants() {
  const { id } = useParams();
  const vid = id ? Number(id) : null;
  const nav = useNavigate();
  const { provider } = useHr();
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [rows, setRows] = useState<Row[] | null>(null);
  const [stage, setStage] = useState<Stage | "all">("all");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const vs = await api.vacancies();
    setVacancies(vs);
    const scope = vid ? vs.filter((v) => v.id === vid) : vs;
    const lists = await Promise.all(scope.map(async (v) => (await api.candidates(v.id)).map((c) => ({ ...c, vacancy_title: v.title }))));
    setRows(lists.flat().sort((a, b) => (b.score ?? -1) - (a.score ?? -1)));
  }, [vid]);

  useEffect(() => {
    setRows(null);
    load();
  }, [load]);

  useEffect(() => {
    if (!rows?.some((r) => r.status === "uploaded" || r.status === "processing")) return;
    const t = setTimeout(load, 1500);
    return () => clearTimeout(t);
  }, [rows, load]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: rows?.length ?? 0 };
    rows?.forEach((r) => (c[r.stage] = (c[r.stage] ?? 0) + 1));
    return c;
  }, [rows]);

  const visible = (rows ?? []).filter((r) => stage === "all" || r.stage === stage);
  const vacancy = vacancies.find((v) => v.id === vid);

  const changeStage = async (r: Row, s: Stage) => {
    setRows((list) => list?.map((x) => (x.id === r.id ? { ...x, stage: s } : x)) ?? null);
    await api.setStage(r.id, s);
  };

  const upload = async (files: File[]) => {
    if (!vid || !files.length) return;
    setUploading(true);
    setError("");
    try {
      await api.upload(vid, files, provider);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="hr-page">
      <header className="hr-head">
        <div>
          <h1>{vacancy ? vacancy.title : "Отклики"}</h1>
          <p className="muted">
            {vacancy
              ? `${vacancy.candidates_count} ${plural(vacancy.candidates_count, "кандидат", "кандидата", "кандидатов")}, из них новых ${vacancy.new_count}`
              : "Все кандидаты по всем вакансиям, лучшие по оценке ИИ — сверху."}
          </p>
        </div>
        {vacancy && (
          <div className="row-gap">
            <Link to={`/hr/vacancies/${vacancy.id}/edit`} className="btn btn-soft">
              Редактировать вакансию
            </Link>
            <button className="btn btn-primary" onClick={() => input.current?.click()} disabled={uploading}>
              <IconUpload size={18} /> {uploading ? "Загружаю…" : "Загрузить резюме"}
            </button>
            <input ref={input} type="file" multiple accept=".pdf,.docx,.txt" hidden onChange={(e) => upload(Array.from(e.target.files ?? []))} />
          </div>
        )}
      </header>

      <div className="filters">
        <div className="chips" role="tablist" aria-label="Вакансия">
          <Link to="/hr" className={`chip ${!vid ? "on" : ""}`}>
            Все вакансии
          </Link>
          {vacancies.map((v) => (
            <Link key={v.id} to={`/hr/vacancies/${v.id}`} className={`chip ${vid === v.id ? "on" : ""}`}>
              {v.title}
              {v.new_count > 0 && <span className="badge">{v.new_count}</span>}
            </Link>
          ))}
        </div>
        <div className="chips" role="tablist" aria-label="Этап">
          {(["all", ...STAGES] as const).map((s) => (
            <button key={s} className={`chip small ${stage === s ? "on" : ""}`} onClick={() => setStage(s)}>
              {s === "all" ? "Все этапы" : STAGE_FOR_HR[s]} <span className="count">{counts[s] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}

      {rows === null ? (
        <p className="muted">Загружаем отклики…</p>
      ) : visible.length === 0 ? (
        <div className="empty-state">
          <Eye mood="sleepy" size={130} track={false} />
          <p>{rows.length ? "На этом этапе пока никого." : "Откликов пока нет. Опубликуйте вакансию или загрузите резюме вручную."}</p>
        </div>
      ) : (
        <table className="applicants">
          <thead>
            <tr>
              <th>Кандидат</th>
              {!vid && <th>Вакансия</th>}
              <th>Оценка ИИ</th>
              <th>Этап</th>
              <th>Получен</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.id} onClick={() => nav(`/hr/candidates/${r.id}`)} className={r.stage === "new" ? "is-new" : ""}>
                <td>
                  <Link to={`/hr/candidates/${r.id}`} className="cand-name" onClick={(e) => e.stopPropagation()}>
                    {r.name || r.filename}
                  </Link>
                  <span className="muted small">{r.source === "site" ? "Отклик с сайта" : "Загружен вручную"}</span>
                </td>
                {!vid && <td className="muted">{r.vacancy_title}</td>}
                <td>
                  {r.status === "screened" && r.score != null ? (
                    <span className={`score-pill v-${r.verdict}`}>
                      <b>{Math.round(r.score)}</b> {r.verdict && VERDICT[r.verdict]}
                    </span>
                  ) : r.status === "failed" ? (
                    <span className="muted">ошибка разбора</span>
                  ) : (
                    <span className="muted">читаю резюме…</span>
                  )}
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  <select className={`stage-select s-${r.stage}`} value={r.stage} onChange={(e) => changeStage(r, e.target.value as Stage)} aria-label="Этап">
                    {STAGES.map((s) => (
                      <option key={s} value={s}>
                        {STAGE_FOR_HR[s]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="muted">{date(r.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
