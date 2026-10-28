import type { Analytics, Candidate, CandidateDetail, ChatMessage, Provider, ToolTrace, Vacancy } from "./types";

const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-key";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", API_KEY);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not json */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export const api = {
  providers: () => request<Provider[]>("/providers"),
  vacancies: () => request<Vacancy[]>("/vacancies"),
  createVacancy: (body: { title: string; company: string; description: string }) =>
    request<Vacancy>("/vacancies", { method: "POST", body: JSON.stringify(body) }),
  candidates: (vid: number) => request<Candidate[]>(`/vacancies/${vid}/candidates`),
  upload: (vid: number, files: File[], provider: string) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    return request<Candidate[]>(`/vacancies/${vid}/candidates?provider=${provider}`, { method: "POST", body: fd });
  },
  candidate: (cid: number) => request<CandidateDetail>(`/candidates/${cid}`),
  rescreen: (cid: number, provider: string) => request(`/candidates/${cid}/rescreen?provider=${provider}`, { method: "POST" }),
  exportTo: (cid: number, system: "bitrix24" | "1c") =>
    request<{ status: string; external_id: string }>(`/candidates/${cid}/export?system=${system}`, { method: "POST" }),
  remove: (cid: number) => request(`/candidates/${cid}`, { method: "DELETE" }),
  analytics: (vid: number) => request<Analytics>(`/vacancies/${vid}/analytics`),
  chat: (vid: number, messages: ChatMessage[], provider: string) =>
    request<{ answer: string; tool_calls: ToolTrace[] }>(`/agent/chat?provider=${provider}`, {
      method: "POST",
      body: JSON.stringify({ vacancy_id: vid, messages: messages.map(({ role, content }) => ({ role, content })) }),
    }),
};
