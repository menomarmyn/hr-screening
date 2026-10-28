import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Vacancy } from "../types";

const SUGGESTIONS = [
  "Покажи топ-5 кандидатов",
  "У кого есть опыт с 1С или Битрикс24?",
  "Кто разворачивал локальные LLM?",
  "Сравни кандидатов 1 и 6",
];

export function AgentChat({ vacancy, provider }: { vacancy: Vacancy; provider: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      setMessages([...next, { role: "assistant", content: `Ошибка: ${(e as Error).message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card chat">
      <div className="chat-log">
        {messages.length === 0 && (
          <div className="empty">
            <p>Ассистент отвечает по кандидатам этой вакансии, вызывая инструменты: рейтинг, семантический поиск по резюме, сравнение, выгрузка в CRM/1С.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip-btn" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.tools?.map((t, j) => (
              <details key={j} className="tool">
                <summary className="mono">
                  ⚙ {t.name}({Object.entries(t.arguments).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})
                </summary>
                <pre>{t.result_preview}</pre>
              </details>
            ))}
            <div className="bubble">{m.content}</div>
          </div>
        ))}
        {busy && <span className="spinner" />}
        <div ref={end} />
      </div>
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Спросите о кандидатах…" />
        <button className="btn primary" disabled={busy}>
          Отправить
        </button>
      </form>
    </section>
  );
}
