import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { IconClose, IconPlus } from "../illustrations/Icons";
import type { Company } from "../types";

type Form = Omit<Company, "open_jobs">;

export function CompanyEdit() {
  const [f, setF] = useState<Form | null>(null);
  const [saved, setSaved] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.company().then(({ open_jobs: _ignored, ...rest }) => setF(rest));
  }, []);

  if (!f) return <div className="hr-page muted">Загружаем…</div>;
  const set = <K extends keyof Form>(k: K, v: Form[K]) => {
    setF({ ...f, [k]: v });
    setSaved("");
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.saveCompany(f);
      setSaved("Сохранено. Изменения уже на сайте.");
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form className="hr-page editor" onSubmit={save}>
      <header className="hr-head">
        <div>
          <h1>Страница компании</h1>
          <p className="muted">Это кандидаты видят на главной сайта.</p>
        </div>
        <Link to="/" className="btn btn-soft" target="_blank">
          Открыть сайт
        </Link>
      </header>
      <div className="form-grid">
        <label className="field">
          <span>Название</span>
          <input value={f.name} onChange={(e) => set("name", e.target.value)} required />
        </label>
        <label className="field">
          <span>Город</span>
          <input value={f.location} onChange={(e) => set("location", e.target.value)} />
        </label>
        <label className="field span-2">
          <span>Главная фраза</span>
          <input value={f.tagline} onChange={(e) => set("tagline", e.target.value)} placeholder="Крупный заголовок на главной" />
        </label>
        <label className="field span-2">
          <span>О компании</span>
          <textarea rows={5} value={f.about} onChange={(e) => set("about", e.target.value)} />
        </label>
        <label className="field">
          <span>Сайт</span>
          <input value={f.website} onChange={(e) => set("website", e.target.value)} placeholder="https://" />
        </label>
        <label className="field">
          <span>Email для кандидатов</span>
          <input type="email" value={f.contact_email} onChange={(e) => set("contact_email", e.target.value)} />
        </label>
      </div>

      <section className="list-editor">
        <h2>Почему к нам</h2>
        <p className="muted small">Три коротких пункта лучше, чем десять.</p>
        <ul className="highlight-edit">
          {f.highlights.map((h, i) => (
            <li key={i}>
              <input value={h.title} placeholder="Заголовок" onChange={(e) => set("highlights", f.highlights.map((x, j) => (j === i ? { ...x, title: e.target.value } : x)))} />
              <input value={h.text} placeholder="Одно предложение" onChange={(e) => set("highlights", f.highlights.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))} />
              <button type="button" className="icon-btn" onClick={() => set("highlights", f.highlights.filter((_, j) => j !== i))} aria-label="Удалить пункт">
                <IconClose />
              </button>
            </li>
          ))}
        </ul>
        <button type="button" className="add-btn" onClick={() => set("highlights", [...f.highlights, { title: "", text: "" }])}>
          <IconPlus /> Добавить пункт
        </button>
      </section>

      {error && <p className="form-error">{error}</p>}
      <div className="editor-foot">
        <button className="btn btn-primary btn-lg">Сохранить</button>
        {saved && <span className="note">{saved}</span>}
      </div>
    </form>
  );
}
