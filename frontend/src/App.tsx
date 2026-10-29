import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { ApplicantDetail } from "./hr/ApplicantDetail";
import { Applicants } from "./hr/Applicants";
import { Assistant } from "./hr/Assistant";
import { CompanyEdit } from "./hr/CompanyEdit";
import { HrLayout } from "./hr/HrLayout";
import { Vacancies } from "./hr/Vacancies";
import { VacancyEditor } from "./hr/VacancyEditor";
import { Eye } from "./illustrations/Eye";
import { AuthProvider, RequireRole } from "./lib/auth";
import { AuthPage } from "./site/AuthPage";
import { Home } from "./site/Home";
import { JobPage } from "./site/JobPage";
import { MyApplications } from "./site/MyApplications";
import { SiteLayout } from "./site/SiteLayout";

function NotFound() {
  return (
    <div className="page narrow empty-state">
      <Eye size={150} />
      <h1>Такой страницы нет</h1>
      <p className="muted">Возможно, ссылка устарела.</p>
      <Link to="/" className="btn btn-primary">
        На главную
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<SiteLayout />}>
            <Route index element={<Home />} />
            <Route path="jobs/:id" element={<JobPage />} />
            <Route path="login" element={<AuthPage mode="login" />} />
            <Route path="register" element={<AuthPage mode="register" />} />
            <Route
              path="me"
              element={
                <RequireRole role="candidate">
                  <MyApplications />
                </RequireRole>
              }
            />
            <Route path="*" element={<NotFound />} />
          </Route>
          <Route
            path="hr"
            element={
              <RequireRole role="hr">
                <HrLayout />
              </RequireRole>
            }
          >
            <Route index element={<Applicants />} />
            <Route path="vacancies" element={<Vacancies />} />
            <Route path="vacancies/new" element={<VacancyEditor />} />
            <Route path="vacancies/:id" element={<Applicants />} />
            <Route path="vacancies/:id/edit" element={<VacancyEditor />} />
            <Route path="candidates/:id" element={<ApplicantDetail />} />
            <Route path="company" element={<CompanyEdit />} />
            <Route path="assistant" element={<Assistant />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
