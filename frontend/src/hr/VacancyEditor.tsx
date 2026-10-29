import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconClose, IconPlus, IconSparkle } from "../illustrations/Icons";
import type { Requirement, Vacancy, VacancyDraft } from "../types";
import { useHr } from "./HrLayout";

const EXAMPLE = `Например, как написали бы коллеге:

Ищем бэкенд-разработчика на Python в Алматы, можно гибрид. Будет писать API на FastAPI и подключать LLM к нашим продуктам, иногда ездить к заказчикам. Нужен опыт от 3 лет, Postgres, Docker. Если знает 1С или работал с RAG — вообще отлично. Зарплата от 900 тысяч, ДМС, обучение.`;

const empty: VacancyDraft = { title: "", summary: "", responsibilities: [], requirements: [], conditions: [], location: "", employment: "", salary: "" };

export function VacancyEditor() {
  const { id } = useParams();
  const editing = id ? Number(id) : null;
  const nav = useNavigate();
  const { provider, providers } = useHr();
  const [step, setStep] = useState<"text" | "form">(editing ? "form" : "text");
  const [text, setText] = useState("");
  const [draft, setDraft] = useState<VacancyDraft>(empty);
  const [status, setStatus] = useState<Vacancy["status"]>("open");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!editing) return;
    api.vacancy(editing).then((v) => {
      setDraft(v);
      setText(v.description);
      setStatus(v.status);
    });
  }, [editing]);

  const parse = async () => {
    setBusy(true);
    setError("");
    try {
      const d = await api.parseVacancy(text, provider);
      setDraft(d);
      setStep("form");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const save = async (st: Vacancy["status"]) => {
    setBusy(true);
    setError("");
    try {
      const body = { ...draft, description: text, status: st };
      const v = editing ? await api.updateVacancy(editing, body) : await api.createVacancy(body);
      nav(`/hr/vacancies/${v.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const set = <K extends keyof VacancyDraft>(k: K, v: VacancyDraft[K]) => setDraft((d) => ({ ...d, [k]: v }));
  const usingMock = providers.find((p) => p.name === provider)?.name === "mock";

  if (step === "text")
    return (
      <div className="hr-page editor">
        <Link to="/hr/vacancies" className="back">
          Вакансии
        </Link>
        <h1>Новая вакансия</h1>
        <p className="muted lead-sm">Напишите или вставьте текст как есть — заметками, абзацем или готовым объявлением. ИИ разложит его по полям, а вы поправите.</p>
        <label className="field">
          <span className="sr-only">Текст вакансии</span>
          <textarea className="big-text" rows={14} value={text} onChange={(e) => setText(e.target.value)} placeholder={EXAMPLE} autoFocus />
        </label>
        {usingMock && <p className="hint">Сейчас выбран режим без ИИ — он разберёт текст попроще. С ключом OpenAI или Gemini результат будет точнее.</p>}
        {error && <p className="form-error">{error}</p>}
        <div className="row-gap">
          <button className="btn btn-primary btn-lg" onClick={parse} disabled={busy || text.trim().length < 20}>
            <IconSparkle /> {busy ? "Читаю текст…" : "Разобрать текст"}
          </button>
          <button className="btn btn-ghost" onClick={() => setStep("form")}>
            Заполнить вручную
          </button>
        </div>
        {busy && (
          <div className="thinking" aria-live="polite">
            <Eye size={90} track={false} /> <span>Читаю и раскладываю по полям…</span>
          </div>
        )}
      </div>
    );

  return (
    <div className="hr-page editor">
      <Link to={editing ? `/hr/vacancies/${editing}` : "/hr/vacancies"} className="back">
        {editing ? "К откликам" : "Вакансии"}
      </Link>
      <div className="editor-head">
        <h1>{editing ? "Редактирование" : "Проверьте вакансию"}</h1>
        {!editing && (
          <button className="link-btn" onClick={() => setStep("text")}>
            Вернуться к тексту
          </button>
        )}
      </div>
      {!editing && <p className="muted lead-sm">Так вакансию увидят кандидаты. Требования ниже ИИ использует, чтобы оценивать резюме, — проверьте их внимательнее всего.</p>}

      <div className="form-grid">
        <label className="field span-2">
          <span>Должность</span>
          <input value={draft.title} onChange={(e) => set("title", e.target.value)} placeholder="Python-разработчик" />
        </label>
        <label className="field span-2">
          <span>Коротко о работе</span>
          <textarea rows={3} value={draft.summary} onChange={(e) => set("summary", e.target.value)} placeholder="Две-три фразы для кандидата: чем предстоит заниматься" />
        </label>
        <label className="field">
          <span>Город</span>
          <input value={draft.location} onChange={(e) => set("location", e.target.value)} />
        </label>
        <label className="field">
          <span>Формат работы</span>
          <input value={draft.employment} onChange={(e) => set("employment", e.target.value)} placeholder="офис, гибрид, удалённо" />
        </label>
        <label className="field span-2">
          <span>Зарплата</span>
          <input value={draft.salary} onChange={(e) => set("salary", e.target.value)} placeholder="Можно оставить пустым" />
        </label>
      </div>

      <ListEditor title="Чем предстоит заниматься" items={draft.responsibilities} onChange={(v) => set("responsibilities", v)} placeholder="Новая обязанность" />
      <RequirementsEditor items={draft.requirements} onChange={(v) => set("requirements", v)} />
      <ListEditor title="Что предлагаете" items={draft.conditions} onChange={(v) => set("conditions", v)} placeholder="Например, ДМС" />

      {error && <p className="form-error">{error}</p>}
      <div className="editor-foot">
        {editing ? (
          <>
            <label className="field compact">
              <span>Статус</span>
              <select value={status} onChange={(e) => setStatus(e.target.value as Vacancy["status"])}>
                <option value="open">Опубликована</option>
                <option value="draft">Черновик</option>
                <option value="closed">Приём закрыт</option>
              </select>
            </label>
            <button className="btn btn-primary btn-lg" onClick={() => save(status)} disabled={busy}>
              Сохранить
            </button>
          </>
        ) : (
          <>
            <button className="btn btn-primary btn-lg" onClick={() => save("open")} disabled={busy || !draft.title || !draft.requirements.length}>
              Опубликовать
            </button>
            <button className="btn btn-soft" onClick={() => save("draft")} disabled={busy || !draft.title}>
              Сохранить черновик
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function ListEditor({ title, items, onChange, placeholder }: { title: string; items: string[]; onChange: (v: string[]) => void; placeholder: string }) {
  return (
    <section className="list-editor">
      <h2>{title}</h2>
      <ul>
        {items.map((x, i) => (
          <li key={i}>
            <input value={x} onChange={(e) => onChange(items.map((y, j) => (j === i ? e.target.value : y)))} />
            <button className="icon-btn" onClick={() => onChange(items.filter((_, j) => j !== i))} aria-label="Удалить пункт">
              <IconClose />
            </button>
          </li>
        ))}
      </ul>
      <button className="add-btn" onClick={() => onChange([...items, ""])}>
        <IconPlus /> {placeholder}
      </button>
    </section>
  );
}

function RequirementsEditor({ items, onChange }: { items: Requirement[]; onChange: (v: Requirement[]) => void }) {
  const update = (i: number, patch: Partial<Requirement>) => onChange(items.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  return (
    <section className="list-editor reqs-editor">
      <h2>Требования к кандидату</h2>
      <p className="muted small">«Обязательно» весит в оценке вдвое больше, чем «плюсом».</p>
      <ul>
        {items.map((r, i) => (
          <li key={r.id || i}>
            <input value={r.text} onChange={(e) => update(i, { text: e.target.value })} />
            <button className={`kind-toggle k-${r.kind}`} onClick={() => update(i, { kind: r.kind === "must" ? "nice" : "must" })} title="Переключить">
              {r.kind === "must" ? "Обязательно" : "Плюсом"}
            </button>
            <button className="icon-btn" onClick={() => onChange(items.filter((_, j) => j !== i))} aria-label="Удалить требование">
              <IconClose />
            </button>
          </li>
        ))}
      </ul>
      <button className="add-btn" onClick={() => onChange([...items, { id: "", text: "", kind: "must", category: "soft" }])}>
        <IconPlus /> Добавить требование
      </button>
    </section>
  );
}
