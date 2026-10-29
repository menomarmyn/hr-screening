import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Vacancy } from "../types";
import { useHr } from "./HrLayout";

const SUGGESTIONS = ["Покажи пятёрку лучших", "У кого есть опыт с 1С или Битрикс24?", "Кто разворачивал локальные LLM?", "Сравни кандидатов 1 и 6"];

const TOOL: Record<string, string> = {
  rank_candidates: "смотрю рейтинг",
  search_candidates: "ищу по резюме",
  get_candidate: "открываю карточку",
  compare_candidates: "сравниваю",
  export_candidate: "выгружаю",
  vacancy_requirements: "смотрю требования",
};

export function Assistant() {
  const { provider } = useHr();
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [vid, setVid] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.vacancies().then((vs) => {
      setVacancies(vs);
      setVid(vs[0]?.id ?? null);
    });
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const send = async (text: string) => {
    if (!vid || !text.trim() || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api.chat(vid, next, provider);
      setMessages([...next, { role: "assistant", content: r.answer, tools: r.tool_calls }]);
    } catch (e) {
      setMessages([...next, { role: "assistant", content: `Не получилось: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="hr-page assistant">
      <header className="hr-head">
        <div>
          <h1>Ассистент</h1>
          <p className="muted">Отвечает по откликам выбранной вакансии и показывает, какие данные смотрел.</p>
        </div>
        <label className="field compact">
          <span>Вакансия</span>
          <select
            value={vid ?? ""}
            onChange={(e) => {
              setVid(Number(e.target.value));
              setMessages([]);
            }}
          >
            {vacancies.map((v) => (
              <option key={v.id} value={v.id}>
                {v.title}
              </option>
            ))}
          </select>
        </label>
      </header>

      <div className="chat">
        <div className="chat-log" aria-live="polite">
          {messages.length === 0 && (
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.tools?.map((t, j) => (
                <details key={j} className="tool">
                  <summary>{TOOL[t.name] ?? t.name}</summary>
                  <pre>{t.result_preview}</pre>
                </details>
              ))}
              <div className="bubble">{m.content}</div>
            </div>
          ))}
          {busy && <p className="muted">Думаю…</p>}
          <div ref={end} />
        </div>
        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Спросите о кандидатах" aria-label="Вопрос ассистенту" />
          <button className="btn btn-primary" disabled={busy || !input.trim()}>
            Спросить
          </button>
        </form>
      </div>
    </div>
  );
}
