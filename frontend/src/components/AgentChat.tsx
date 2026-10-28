import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Vacancy } from "../types";
import { Spinner } from "./ui";

const SUGGESTIONS = ["Покажи топ-5 кандидатов", "У кого есть опыт с 1С или Битрикс24?", "Кто разворачивал локальные LLM?", "Сравни кандидатов 1 и 6"];

const TOOL_LABEL: Record<string, string> = {
  rank_candidates: "Рейтинг",
  search_candidates: "Поиск по резюме",
  get_candidate: "Карточка кандидата",
  compare_candidates: "Сравнение",
  export_candidate: "Выгрузка",
  vacancy_requirements: "Требования вакансии",
};

export function AgentChat({ vacancy, provider }: { vacancy: Vacancy; provider: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const r = await api.chat(vacancy.id, next, provider);
      setMessages([...next, { role: "assistant", content: r.answer, tools: r.tool_calls }]);
    } catch (e) {
      setMessages([...next, { role: "assistant", content: `Не получилось ответить: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="chat">
      <div className="chat-log" aria-live="polite">
        {messages.length === 0 && (
          <div className="chat-intro">
            <h2>Спросите о кандидатах</h2>
            <p className="muted">
              Ассистент отвечает только по данным этой вакансии: смотрит рейтинг, ищет по текстам резюме, сравнивает кандидатов и по вашей просьбе отправляет их в CRM. Каждое обращение к данным видно в ответе.
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="suggestion" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.tools && m.tools.length > 0 && (
              <div className="tools">
                {m.tools.map((t, j) => (
                  <details key={j} className="tool">
                    <summary>
                      {TOOL_LABEL[t.name] ?? t.name}
                      <span className="tool-args">
                        {Object.entries(t.arguments)
                          .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
                          .join(", ")}
                      </span>
                    </summary>
                    <pre>{t.result_preview}</pre>
                  </details>
                ))}
              </div>
            )}
            <div className="bubble">{m.content}</div>
          </div>
        ))}
        {busy && <Spinner label="Ассистент работает с данными" />}
        <div ref={end} />
      </div>
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <label className="sr-only" htmlFor="ask">
          Вопрос ассистенту
        </label>
        <input id="ask" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Например: кто из кандидатов работал с pgvector?" />
        <button className="btn primary" disabled={busy || !input.trim()}>
          Спросить
        </button>
      </form>
    </section>
  );
}
