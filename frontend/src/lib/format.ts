import type { Stage, Verdict } from "../types";

export function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

export function date(iso: string) {
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
}

/** Как этап видит кандидат — спокойные формулировки, без «отказа» капсом */
export const STAGE_FOR_CANDIDATE: Record<Stage, string> = {
  new: "Отклик получен",
  review: "Резюме смотрят",
  interview: "Приглашение на интервью",
  offer: "Предложение о работе",
  rejected: "Не в этот раз",
};

export const STAGE_FOR_HR: Record<Stage, string> = {
  new: "Новый",
  review: "Смотрим",
  interview: "Интервью",
  offer: "Оффер",
  rejected: "Отказ",
};

export const STAGES: Stage[] = ["new", "review", "interview", "offer", "rejected"];

export const VERDICT: Record<Verdict, string> = { strong: "Сильный", maybe: "Возможно", reject: "Не подходит" };
