import type { Candidate, CandidateDetail, ChatMessage, Company, MyApplication, Provider, PublicJob, Stage, ToolTrace, User, Vacancy, VacancyDraft } from "./types";

const TOKEN_KEY = "koz.token";

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(t: string | null) {
    try {
      if (t) localStorage.setItem(TOKEN_KEY, t);
      else localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* приватный режим — живём без сохранения */
    }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let onUnauthorized: () => void = () => {};
export const setUnauthorizedHandler = (fn: () => void) => (onUnauthorized = fn);

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* не JSON */
    }
    if (res.status === 401 && token) onUnauthorized();
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? "Проверьте поля формы" : "Что-то пошло не так";
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);

export const api = {
  // авторизация
  register: (b: { email: string; password: string; full_name: string; role: "candidate" | "hr"; invite_code?: string }) =>
    request<{ token: string; user: User }>("/auth/register", { method: "POST", body: json(b) }),
  login: (email: string, password: string) => request<{ token: string; user: User }>("/auth/login", { method: "POST", body: json({ email, password }) }),
  me: () => request<User>("/auth/me"),

  // публичная часть
  company: () => request<Company>("/company"),
  jobs: () => request<PublicJob[]>("/jobs"),
  job: (id: number) => request<PublicJob>(`/jobs/${id}`),
  apply: (id: number, file: File, cover_letter: string) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("cover_letter", cover_letter);
    return request<MyApplication>(`/jobs/${id}/apply`, { method: "POST", body: fd });
  },
  myApplications: () => request<MyApplication[]>("/me/applications"),
  withdraw: (id: number) => request(`/me/applications/${id}`, { method: "DELETE" }),

  // HR
  providers: () => request<Provider[]>("/providers"),
  saveCompany: (c: Omit<Company, "open_jobs">) => request<Company>("/company", { method: "PUT", body: json(c) }),
  parseVacancy: (text: string, provider?: string) => request<VacancyDraft>(`/vacancies/parse${provider ? `?provider=${provider}` : ""}`, { method: "POST", body: json({ text }) }),
  vacancies: () => request<Vacancy[]>("/vacancies"),
  vacancy: (id: number) => request<Vacancy>(`/vacancies/${id}`),
  createVacancy: (v: Partial<Vacancy>) => request<Vacancy>("/vacancies", { method: "POST", body: json(v) }),
  updateVacancy: (id: number, v: Partial<Vacancy>) => request<Vacancy>(`/vacancies/${id}`, { method: "PUT", body: json(v) }),
  candidates: (vid: number) => request<Candidate[]>(`/vacancies/${vid}/candidates`),
  upload: (vid: number, files: File[], provider?: string) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<Candidate[]>(`/vacancies/${vid}/candidates${provider ? `?provider=${provider}` : ""}`, { method: "POST", body: fd });
  },
  candidate: (id: number) => request<CandidateDetail>(`/candidates/${id}`),
  setStage: (id: number, stage: Stage) => request<Candidate>(`/candidates/${id}/stage`, { method: "PATCH", body: json({ stage }) }),
  rescreen: (id: number, provider?: string) => request(`/candidates/${id}/rescreen${provider ? `?provider=${provider}` : ""}`, { method: "POST" }),
  exportTo: (id: number, system: "bitrix24" | "1c") => request<{ status: string }>(`/candidates/${id}/export?system=${system}`, { method: "POST" }),
  removeCandidate: (id: number) => request(`/candidates/${id}`, { method: "DELETE" }),
  chat: (vid: number, messages: ChatMessage[], provider?: string) =>
    request<{ answer: string; tool_calls: ToolTrace[] }>(`/agent/chat${provider ? `?provider=${provider}` : ""}`, {
      method: "POST",
      body: json({ vacancy_id: vid, messages: messages.map(({ role, content }) => ({ role, content })) }),
    }),

  /** Файл резюме с авторизацией → blob URL для просмотра в iframe */
  fileUrl: async (id: number) => {
    const token = tokenStore.get();
    const res = await fetch(`/api/applications/${id}/file`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
    if (!res.ok) throw new ApiError(res.status, "Файл недоступен");
    return URL.createObjectURL(await res.blob());
  },
};
