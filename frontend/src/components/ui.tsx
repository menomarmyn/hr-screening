import type { MatchStatus, Requirement, Verdict } from "../types";

const VERDICT_LABEL: Record<Verdict, string> = { strong: "Пригласить", maybe: "Рассмотреть", reject: "Отказ" };
const STATUS_LABEL: Record<MatchStatus, string> = { met: "подтверждено", partial: "частично", missing: "нет данных" };

export function VerdictTag({ verdict }: { verdict: Verdict }) {
  return <span className={`verdict v-${verdict}`}>{VERDICT_LABEL[verdict]}</span>;
}

export function Score({ score, verdict, size = "md" }: { score: number; verdict?: Verdict | null; size?: "md" | "xl" }) {
  return (
    <span className={`score score-${size} ${verdict ? `v-${verdict}` : ""}`} aria-label={`${Math.round(score)} из 100`}>
      {Math.round(score)}
    </span>
  );
}

/** «Отпечаток» кандидата: одна ячейка на требование, обязательные слева, «плюсом» справа. */
export function Fingerprint({ statuses, requirements, size = "sm" }: { statuses: MatchStatus[]; requirements: Requirement[]; size?: "sm" | "lg" }) {
  if (!statuses.length) return <span className={`fp fp-${size} fp-empty`} />;
  const cells = requirements.map((r, i) => ({ r, s: statuses[i] ?? "missing" }));
  const must = cells.filter((c) => c.r.kind === "must");
  const nice = cells.filter((c) => c.r.kind === "nice");
  const render = (list: typeof cells) =>
    list.map(({ r, s }) => <span key={r.id} className={`fp-cell s-${s}`} title={`${r.text}: ${STATUS_LABEL[s]}`} />);
  return (
    <span className={`fp fp-${size}`} role="img" aria-label={`Подтверждено ${statuses.filter((s) => s === "met").length} из ${statuses.length} требований`}>
      <span className="fp-group">{render(must)}</span>
      {nice.length > 0 && <span className="fp-group nice">{render(nice)}</span>}
    </span>
  );
}

export function StatusDot({ status }: { status: MatchStatus }) {
  return <span className={`dot s-${status}`} aria-label={STATUS_LABEL[status]} />;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="spinner-wrap" role="status">
      <span className="spinner" />
      {label && <span>{label}</span>}
    </span>
  );
}

export function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}
