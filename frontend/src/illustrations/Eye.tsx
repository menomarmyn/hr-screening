import { useEffect, useId, useRef, useState, type RefObject } from "react";

/**
 * Персонаж сайта — глаз («көз» по-казахски). Нарисован вручную в SVG.
 * open    — смотрит на курсор и иногда моргает;
 * curious — то же, бровь приподнята (наведение на главное действие);
 * sleepy  — закрыт, для пустых состояний;
 * happy   — улыбается, после успешного действия.
 */
export type EyeMood = "open" | "curious" | "sleepy" | "happy";

const reduceMotion = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

export function Eye({
  mood = "open",
  size = 240,
  track = true,
  lookAt,
  className = "",
  title,
}: {
  mood?: EyeMood;
  size?: number;
  track?: boolean;
  lookAt?: RefObject<HTMLElement> | null;
  className?: string;
  title?: string;
}) {
  const svg = useRef<SVGSVGElement>(null);
  const [gaze, setGaze] = useState({ x: 0, y: 0 });
  const clip = useId().replace(/:/g, "");

  useEffect(() => {
    if (!track || mood === "sleepy" || mood === "happy" || reduceMotion()) return;
    const aim = (px: number, py: number) => {
      const box = svg.current?.getBoundingClientRect();
      if (!box) return;
      const cx = box.left + box.width / 2;
      const cy = box.top + box.height * 0.56;
      const dx = px - cx;
      const dy = py - cy;
      const dist = Math.hypot(dx, dy) || 1;
      const reach = Math.min(1, dist / (box.width * 1.4));
      setGaze({ x: (dx / dist) * 30 * reach, y: (dy / dist) * 17 * reach });
    };
    if (lookAt?.current) {
      const b = lookAt.current.getBoundingClientRect();
      aim(b.left + b.width / 2, b.top + b.height / 2);
      return;
    }
    const onMove = (e: PointerEvent) => aim(e.clientX, e.clientY);
    const onLeave = () => setGaze({ x: 0, y: 0 });
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
    };
  }, [track, mood, lookAt]);

  const height = (size * 170) / 240;
  return (
    <svg
      ref={svg}
      className={`eye eye-${mood} ${className}`}
      width={size}
      height={height}
      viewBox="0 0 240 170"
      role={title ? "img" : undefined}
      aria-hidden={title ? undefined : true}
      aria-label={title}
    >
      <defs>
        <clipPath id={`lid-${clip}`}>
          <path d="M22 98 Q120 14 218 98 Q120 182 22 98 Z" />
        </clipPath>
      </defs>

      {/* бровь — у счастливого глаза её нет, иначе две дуги читаются как хмурость */}
      <path style={{ display: mood === "happy" ? "none" : undefined }} className="eye-brow" d="M62 30 Q120 4 178 30" fill="none" stroke="var(--eye-ink)" strokeWidth="8" strokeLinecap="round" />

      {mood === "sleepy" && (
        <g className="eye-sleep">
          <path d="M28 100 Q120 150 212 100" fill="none" stroke="var(--eye-ink)" strokeWidth="7" strokeLinecap="round" />
          <path d="M70 124 l-8 14 M120 132 v16 M170 124 l8 14" stroke="var(--eye-ink)" strokeWidth="6" strokeLinecap="round" />
          <text x="200" y="52" className="eye-z">z</text>
          <text x="216" y="30" className="eye-z small">z</text>
        </g>
      )}

      {mood === "happy" && (
        <g className="eye-happy">
          <path d="M34 112 Q120 28 206 112" fill="none" stroke="var(--eye-ink)" strokeWidth="8" strokeLinecap="round" />
          <ellipse cx="44" cy="138" rx="20" ry="9" fill="var(--eye-blush)" />
          <ellipse cx="196" cy="138" rx="20" ry="9" fill="var(--eye-blush)" />
          <path className="eye-spark" d="M214 40 l0 -16 M206 32 l16 0" stroke="var(--eye-amber)" strokeWidth="5" strokeLinecap="round" />
        </g>
      )}

      {(mood === "open" || mood === "curious") && (
        <g className="eye-ball">
          {/* ресницы */}
          <path d="M58 58 l-12 -14 M92 40 l-6 -17 M148 40 l6 -17 M182 58 l12 -14" stroke="var(--eye-ink)" strokeWidth="6" strokeLinecap="round" />
          <path d="M22 98 Q120 14 218 98 Q120 182 22 98 Z" fill="var(--eye-white)" />
          <g clipPath={`url(#lid-${clip})`}>
            <g className="eye-iris" style={{ transform: `translate(${gaze.x}px, ${gaze.y}px)` }}>
              <circle cx="120" cy="98" r="45" fill="var(--eye-iris)" />
              <circle cx="120" cy="98" r="45" fill="none" stroke="var(--eye-iris-deep)" strokeWidth="5" />
              <circle cx="120" cy="98" r="29" fill="none" stroke="var(--eye-amber)" strokeWidth="7" opacity=".9" />
              <circle cx="120" cy="98" r="18" fill="var(--eye-pupil)" />
              <circle cx="105" cy="83" r="8" fill="#fff" />
              <circle cx="135" cy="110" r="3.5" fill="#fff" opacity=".8" />
            </g>
          </g>
          <path d="M22 98 Q120 14 218 98 Q120 182 22 98 Z" fill="none" stroke="var(--eye-ink)" strokeWidth="7" strokeLinejoin="round" />
        </g>
      )}
    </svg>
  );
}
