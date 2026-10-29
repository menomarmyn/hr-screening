import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconCheck } from "../illustrations/Icons";
import { useAuth } from "../lib/auth";
import { STAGE_FOR_CANDIDATE, date } from "../lib/format";
import type { MyApplication, Stage } from "../types";

const STEPS: { key: Stage[]; label: string }[] = [
  { key: ["new"], label: "Отправлен" },
  { key: ["review"], label: "Смотрят резюме" },
  { key: ["interview"], label: "Интервью" },
  { key: ["offer", "rejected"], label: "Решение" },
];

function progress(stage: Stage) {
  return STEPS.findIndex((s) => s.key.includes(stage));
}

export function MyApplications() {
  const { user } = useAuth();
  const [items, setItems] = useState<MyApplication[] | null>(null);

  const load = () => api.myApplications().then(setItems);
  useEffect(() => {
    load();
  }, []);

  const withdraw = async (a: MyApplication) => {
    if (!window.confirm(`Отозвать отклик на «${a.vacancy_title}»? Резюме удалится из компании.`)) return;
    await api.withdraw(a.id);
    load();
  };

  return (
    <div className="page narrow">
      <h1 className="page-title">Мои отклики</h1>
      <p className="muted page-sub">{user?.full_name}, здесь видно, на каком этапе каждый отклик.</p>

      {items === null ? (
        <p className="muted">Загружаем…</p>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Eye mood="sleepy" size={150} track={false} />
          <p>Вы пока никуда не откликались.</p>
          <Link to="/#jobs" className="btn btn-primary">
            Смотреть вакансии
          </Link>
        </div>
      ) : (
        <ul className="my-apps">
          {items.map((a) => {
            const at = progress(a.stage);
            return (
              <li key={a.id} className={`my-app stage-${a.stage}`}>
                <div className="my-app-head">
                  <div>
                    <Link to={`/jobs/${a.vacancy_id}`} className="my-app-title">
                      {a.vacancy_title}
                    </Link>
                    <p className="muted small">
                      Отправлен {date(a.created_at)}, файл {a.filename}
                    </p>
                  </div>
                  <span className="stage-label">{STAGE_FOR_CANDIDATE[a.stage]}</span>
                </div>
                <ol className="tracker" aria-label="Этапы отбора">
                  {STEPS.map((s, i) => (
                    <li key={s.label} className={i < at ? "done" : i === at ? "now" : ""}>
                      <span className="tracker-dot">{i < at && <IconCheck size={12} />}</span>
                      <span>{i === 3 && a.stage === "offer" ? "Оффер" : i === 3 && a.stage === "rejected" ? "Не в этот раз" : s.label}</span>
                    </li>
                  ))}
                </ol>
                <button className="link-btn" onClick={() => withdraw(a)}>
                  Отозвать отклик
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
