import { useState } from "react";
import { api } from "../api";
import type { Vacancy } from "../types";

export function VacancyForm({ onCreated, onCancel }: { onCreated: (v: Vacancy) => void; onCancel?: () => void }) {
  const [title, setTitle] = useState("Fullstack AI Engineer");
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
    <form className="card form" onSubmit={submit}>
      <h1>Новая вакансия</h1>
      <p className="muted">Вставьте текст вакансии целиком — требования будут извлечены автоматически.</p>
      <div className="row">
        <label>
          Должность
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Компания
          <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Название компании" />
        </label>
      </div>
      <label>
        Текст вакансии
        <textarea rows={16} value={description} onChange={(e) => setDescription(e.target.value)} required placeholder="Что мы ожидаем от Вас: ..." />
      </label>
      {error && <div className="alert">{error}</div>}
      <div className="actions">
        {onCancel && (
          <button type="button" className="btn ghost" onClick={onCancel}>
            Отмена
          </button>
        )}
        <button className="btn primary" disabled={busy}>
          {busy ? "Извлекаю требования…" : "Создать"}
        </button>
      </div>
    </form>
  );
}
