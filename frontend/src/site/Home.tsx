import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useOutletContext } from "react-router-dom";
import { api } from "../api";
import { Eye } from "../illustrations/Eye";
import { IconClock, IconCoin, IconPin, SPOTS } from "../illustrations/Icons";
import { plural } from "../lib/format";
import type { Company, PublicJob } from "../types";

export function JobMeta({ job }: { job: Pick<PublicJob, "location" | "employment" | "salary"> }) {
  return (
    <ul className="job-meta">
      {job.location && (
        <li>
          <IconPin /> {job.location}
        </li>
      )}
      {job.employment && (
        <li>
          <IconClock /> {job.employment[0].toUpperCase() + job.employment.slice(1)}
        </li>
      )}
      {job.salary && (
        <li>
          <IconCoin /> {job.salary}
        </li>
      )}
    </ul>
  );
}

export function Home() {
  const company = useOutletContext<Company | null>();
  const [jobs, setJobs] = useState<PublicJob[] | null>(null);
  const [curious, setCurious] = useState(false);
  const cta = useRef<HTMLAnchorElement>(null);
  const loc = useLocation();

  useEffect(() => {
    api.jobs().then(setJobs).catch(() => setJobs([]));
  }, []);

  useEffect(() => {
    if (loc.hash && jobs) document.querySelector(loc.hash)?.scrollIntoView({ behavior: "smooth" });
  }, [loc.hash, jobs]);

  const n = jobs?.length ?? 0;

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <h1>{(company?.tagline || "Работа, которую видно").replace(/-/g, "\u2011")}</h1>
          <p className="hero-sub">
            {company?.name ? `${company.name} ищет людей в команду.` : "Мы ищем людей в команду."} Откликнуться можно за пару минут — нужен только PDF с резюме.
          </p>
          <div className="hero-actions">
            <a
              ref={cta}
              href="#jobs"
              className="btn btn-primary btn-lg"
              onMouseEnter={() => setCurious(true)}
              onMouseLeave={() => setCurious(false)}
              onFocus={() => setCurious(true)}
              onBlur={() => setCurious(false)}
            >
              Смотреть вакансии
            </a>
            {jobs && (
              <span className="hero-count">
                {n ? `${n} ${plural(n, "открытая вакансия", "открытые вакансии", "открытых вакансий")}` : "Сейчас открытых вакансий нет"}
              </span>
            )}
          </div>
        </div>
        <div className="hero-art">
          <div className="hero-halo" aria-hidden>
            <span />
            <span />
            <span />
          </div>
          <Eye size={300} mood={curious ? "curious" : "open"} lookAt={curious ? cta : null} className="hero-eye" title="Глаз-талисман следит за курсором" />
        </div>
      </section>

      <section id="jobs" className="section">
        <h2 className="section-title">Открытые вакансии</h2>
        {jobs === null ? (
          <p className="muted">Загружаем вакансии…</p>
        ) : jobs.length === 0 ? (
          <div className="empty-state">
            <Eye mood="sleepy" size={140} track={false} />
            <p>Сейчас мы никого не ищем. Загляните позже — новые вакансии появляются здесь первыми.</p>
          </div>
        ) : (
          <ul className="job-list">
            {jobs.map((j) => (
              <li key={j.id}>
                <Link to={`/jobs/${j.id}`} className="job-row">
                  <div className="job-row-main">
                    <h3>{j.title}</h3>
                    <JobMeta job={j} />
                    {j.summary && <p className="job-row-summary">{j.summary}</p>}
                  </div>
                  <span className="job-row-cta">Подробнее</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {company && (company.about || company.highlights.length > 0) && (
        <section id="about" className="section about">
          <h2 className="section-title">О компании</h2>
          <div className="about-grid">
            <p className="about-text">{company.about}</p>
            <ul className="highlights">
              {company.highlights.map((h, i) => {
                const Spot = SPOTS[i % SPOTS.length];
                return (
                  <li key={i}>
                    <Spot size={56} />
                    <div>
                      <h3>{h.title}</h3>
                      <p>{h.text}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      )}
    </>
  );
}
