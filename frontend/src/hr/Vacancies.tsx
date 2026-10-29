import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconPlus } from "../illustrations/Icons";
import { plural } from "../lib/format";
import type { Vacancy } from "../types";

const STATUS: Record<Vacancy["status"], string> = { open: "Опубликована", draft: "Черновик", closed: "Приём закрыт" };

export function Vacancies() {
  const [items, setItems] = useState<Vacancy[] | null>(null);
  useEffect(() => {
    api.vacancies().then(setItems);
  }, []);

  return (
    <div className="hr-page">
      <header className="hr-head">
        <div>
          <h1>Вакансии</h1>
          <p className="muted">Опубликованные видны всем на сайте, черновики — только вам.</p>
        </div>
        <Link to="/hr/vacancies/new" className="btn btn-primary">
          <IconPlus /> Новая вакансия
        </Link>
      </header>
      {items === null ? (
        <p className="muted">Загружаем…</p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Eye mood="sleepy" size={130} track={false} />
          <p>Вакансий пока нет. Начните с текста — ИИ поможет оформить.</p>
        </div>
      ) : (
        <ul className="vac-list">
          {items.map((v) => (
            <li key={v.id}>
              <Link to={`/hr/vacancies/${v.id}`} className="vac-row">
                <span className={`status-dot st-${v.status}`} aria-hidden />
                <span className="vac-title">{v.title}</span>
                <span className="muted">{STATUS[v.status]}</span>
                <span>
                  {v.candidates_count} {plural(v.candidates_count, "отклик", "отклика", "откликов")}
                  {v.new_count > 0 && <span className="badge">+{v.new_count} новых</span>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
