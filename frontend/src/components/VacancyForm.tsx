import { useState } from "react";
import { api } from "../api";
import type { Vacancy } from "../types";

export function VacancyForm({ onCreated, onCancel }: { onCreated: (v: Vacancy) => void; onCancel?: () => void }) {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onCreated(await api.createVacancy({ title, company, description }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="vacancy-form" onSubmit={submit}>
      <h1>Новая вакансия</h1>
      <p className="muted">Вставьте текст вакансии целиком, как на hh.ru. Требования выделятся автоматически, их можно будет поправить.</p>
      <div className="fields">
        <label>
          Должность
          <input value={title} onChange={(e) => setTitle(e.target.value)} required placeholder="Fullstack AI Engineer" />
        </label>
        <label>
          Компания
          <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="KOZ AI" />
        </label>
      </div>
      <label>
        Текст вакансии
        <textarea rows={14} value={description} onChange={(e) => setDescription(e.target.value)} required placeholder={"Что мы ожидаем от Вас:\n— Уверенное владение Python…\n\nБудет преимуществом:\n— Опыт интеграции с 1С…"} />
      </label>
      {error && <div className="alert">{error}</div>}
      <div className="actions">
        <button className="btn primary" disabled={busy}>
          {busy ? "Выделяю требования…" : "Создать вакансию"}
        </button>
        {onCancel && (
          <button type="button" className="btn quiet" onClick={onCancel}>
            Отмена
          </button>
        )}
      </div>
    </form>
  );
}
