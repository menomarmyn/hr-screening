import type { Verdict } from "../types";

const VERDICT_LABEL: Record<Verdict, string> = { strong: "Пригласить", maybe: "Рассмотреть", reject: "Отказ" };

export function VerdictPill({ verdict }: { verdict: Verdict }) {
  return <span className={`pill v-${verdict}`}>{VERDICT_LABEL[verdict]}</span>;
}

export function ScoreBadge({ score, large }: { score: number; large?: boolean }) {
  const tone = score >= 70 ? "hi" : score >= 45 ? "mid" : "lo";
  return (
    <span className={`score ${tone} ${large ? "large" : ""}`}>
      <span className="score-bar" style={{ width: `${Math.min(100, score)}%` }} />
      <span className="score-num">{Math.round(score)}</span>
    </span>
  );
}
