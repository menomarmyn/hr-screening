import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../lib/auth";
import type { Company } from "../types";

export function useCompany() {
  const [c, setC] = useState<Company | null>(null);
  useEffect(() => {
    api.company().then(setC).catch(() => setC(null));
  }, []);
  return c;
}

export function SiteLayout() {
  const { user, signOut } = useAuth();
  const company = useCompany();
  const loc = useLocation();

  useEffect(() => {
    if (!loc.hash) window.scrollTo({ top: 0 });
  }, [loc.pathname, loc.hash]);

  return (
    <div className="site">
      <a className="skip" href="#content">
        К содержимому
      </a>
      <header className="site-head">
        <Link to="/" className="wordmark">
          {company?.name || "Карьера"}
        </Link>
        <nav className="site-nav" aria-label="Основное меню">
          <NavLink to="/#jobs" className="nav-link">
            Вакансии
          </NavLink>
          <NavLink to="/#about" className="nav-link">
            О нас
          </NavLink>
          {user?.role === "candidate" && (
            <NavLink to="/me" className="nav-link">
              Мои отклики
            </NavLink>
          )}
          {user?.role === "hr" && (
            <NavLink to="/hr" className="nav-link">
              Кабинет HR
            </NavLink>
          )}
          {user ? (
            <button className="nav-link as-button" onClick={signOut}>
              Выйти
            </button>
          ) : (
            <Link to="/login" className="btn btn-soft">
              Войти
            </Link>
          )}
        </nav>
      </header>
      <main id="content">
        <Outlet context={company} />
      </main>
      <footer className="site-foot">
        <div>
          <strong>{company?.name}</strong>
          {company?.location && <span>{company.location}</span>}
          {company?.contact_email && <a href={`mailto:${company.contact_email}`}>{company.contact_email}</a>}
        </div>
        <Link to="/login?role=hr" className="foot-link">
          Вход для сотрудников HR
        </Link>
      </footer>
    </div>
  );
}
