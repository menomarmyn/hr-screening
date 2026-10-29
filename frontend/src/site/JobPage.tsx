import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError, api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconClose, IconFile, IconUpload } from "../illustrations/Icons";
import { useAuth } from "../lib/auth";
import { STAGE_FOR_CANDIDATE } from "../lib/format";
import type { MyApplication, PublicJob } from "../types";
import { JobMeta } from "./Home";

export function JobPage() {
  const { id } = useParams();
  const [job, setJob] = useState<PublicJob | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.job(Number(id)).then(setJob).catch((e) => setError(e instanceof ApiError && e.status === 404 ? "Такой вакансии нет или она снята с публикации." : e.message));
  }, [id]);

  if (error)
    return (
      <div className="page narrow empty-state">
        <Eye mood="sleepy" size={140} track={false} />
        <p>{error}</p>
        <Link to="/#jobs" className="btn btn-soft">
          Все вакансии
        </Link>
      </div>
    );
  if (!job) return <div className="page narrow muted">Загружаем…</div>;

  return (
    <div className="page job-page">
      <article className="job-body">
        <Link to="/#jobs" className="back">
          Все вакансии
        </Link>
        <h1>{job.title}</h1>
        <JobMeta job={job} />
        {job.summary && <p className="lead">{job.summary}</p>}
        <JobSection title="Чем предстоит заниматься" items={job.responsibilities} />
        <JobSection title="Что для нас важно" items={job.must} />
        <JobSection title="Будет плюсом" items={job.nice} tone="soft" />
        <JobSection title="Что мы предлагаем" items={job.conditions} />
      </article>
      <aside className="apply-wrap">
        <ApplyPanel job={job} />
      </aside>
    </div>
  );
}

function JobSection({ title, items, tone }: { title: string; items: string[]; tone?: "soft" }) {
  if (!items.length) return null;
  return (
    <section className={`job-section ${tone ?? ""}`}>
      <h2>{title}</h2>
      <ul>
        {items.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ul>
    </section>
  );
}

const ACCEPT = ".pdf,.docx,.txt";
const MAX_MB = 5;

function ApplyPanel({ job }: { job: PublicJob }) {
  const { user } = useAuth();
  const [mine, setMine] = useState<MyApplication | null | undefined>(undefined);
  const [file, setFile] = useState<File | null>(null);
  const [letter, setLetter] = useState("");
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (user?.role !== "candidate") return setMine(null);
    api
      .myApplications()
      .then((list) => setMine(list.find((a) => a.vacancy_id === job.id) ?? null))
      .catch(() => setMine(null));
  }, [user, job.id]);

  const pick = (f: File | undefined) => {
    setError("");
    if (!f) return;
    if (!/\.(pdf|docx|txt)$/i.test(f.name)) return setError("Нужен файл PDF, DOCX или TXT.");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`Файл больше ${MAX_MB} МБ. Сожмите PDF или уберите картинки.`);
    setFile(f);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return setError("Прикрепите резюме.");
    setBusy(true);
    setError("");
    try {
      setMine(await api.apply(job.id, file, letter));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (job.status !== "open")
    return (
      <div className="apply-card">
        <h2>Приём откликов закрыт</h2>
        <p className="muted">Позицию уже закрыли. Посмотрите другие вакансии.</p>
      </div>
    );

  if (!user)
    return (
      <div className="apply-card">
        <h2>Откликнуться</h2>
        <p className="muted">Чтобы отправить резюме и следить за статусом, войдите или создайте аккаунт. Это займёт меньше минуты.</p>
        <div className="stack">
          <Link to={`/register?next=/jobs/${job.id}`} className="btn btn-primary btn-block">
            Создать аккаунт
          </Link>
          <Link to={`/login?next=/jobs/${job.id}`} className="btn btn-soft btn-block">
            У меня есть аккаунт
          </Link>
        </div>
      </div>
    );

  if (user.role === "hr")
    return (
      <div className="apply-card">
        <h2>Вы вошли как HR</h2>
        <p className="muted">Откликаться могут кандидаты. Отклики на эту вакансию — в кабинете.</p>
        <Link to={`/hr/vacancies/${job.id}`} className="btn btn-soft btn-block">
          Открыть отклики
        </Link>
      </div>
    );

  if (mine === undefined) return <div className="apply-card muted">Проверяем ваши отклики…</div>;

  if (mine)
    return (
      <div className="apply-card done">
        <Eye mood="happy" size={120} track={false} />
        <h2>Отклик отправлен</h2>
        <p className="muted">
          Статус: <strong>{STAGE_FOR_CANDIDATE[mine.stage]}</strong>. Мы напишем, когда будет решение.
        </p>
        <Link to="/me" className="btn btn-soft btn-block">
          Мои отклики
        </Link>
      </div>
    );

  return (
    <form className="apply-card" onSubmit={submit}>
      <h2>Откликнуться</h2>
      {file ? (
        <div className="file-chip">
          <IconFile />
          <span className="file-name">{file.name}</span>
          <span className="muted small">{(file.size / 1024 / 1024).toFixed(1)} МБ</span>
          <button type="button" className="icon-btn" onClick={() => setFile(null)} aria-label="Убрать файл">
            <IconClose />
          </button>
        </div>
      ) : (
        <button
          type="button"
          className={`drop ${drag ? "is-drag" : ""}`}
          onClick={() => input.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            pick(e.dataTransfer.files[0]);
          }}
        >
          <IconUpload />
          <span>
            <strong>Прикрепите резюме</strong>
            <span className="muted small">PDF, DOCX или TXT до {MAX_MB} МБ</span>
          </span>
        </button>
      )}
      <input ref={input} type="file" accept={ACCEPT} hidden onChange={(e) => pick(e.target.files?.[0])} />
      <label className="field">
        <span>
          Пара слов о себе <span className="muted">— необязательно</span>
        </span>
        <textarea rows={4} value={letter} onChange={(e) => setLetter(e.target.value)} placeholder="Почему вам интересна эта работа" maxLength={4000} />
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="btn btn-primary btn-block" disabled={busy}>
        {busy ? "Отправляем…" : "Отправить отклик"}
      </button>
      <p className="fine">
        Отправляя отклик, вы соглашаетесь, что компания обработает резюме. Удалить отклик можно в любой момент в личном кабинете.
      </p>
    </form>
  );
}
