/** Иконки нарисованы в одной манере с глазом: скруглённые линии, толщина 2. */
type P = { size?: number; className?: string };

const base = (size: number) => ({ width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true });

export const IconPin = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" />
    <circle cx="12" cy="9.5" r="2.5" />
  </svg>
);

export const IconClock = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </svg>
);

export const IconCoin = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <ellipse cx="12" cy="7" rx="7" ry="3" />
    <path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" />
  </svg>
);

export const IconUpload = ({ size = 22, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 15V4M7.5 8.5 12 4l4.5 4.5" />
    <path d="M4 14v3.5A2.5 2.5 0 0 0 6.5 20h11a2.5 2.5 0 0 0 2.5-2.5V14" />
  </svg>
);

export const IconFile = ({ size = 20, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z" />
    <path d="M14 3v5h5M9 13h6M9 17h4" />
  </svg>
);

export const IconCheck = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </svg>
);

export const IconClose = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M6 6l12 12M18 6 6 18" />
  </svg>
);

export const IconPlus = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconSparkle = ({ size = 18, className }: P) => (
  <svg {...base(size)} className={className}>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.5 6.5l2 2M15.5 15.5l2 2M17.5 6.5l-2 2M8.5 15.5l-2 2" />
  </svg>
);

/* Иллюстрации к «почему мы» — маленькие сцены, а не стоковые пиктограммы */
export const SpotProjects = ({ size = 64 }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
    <rect x="8" y="16" width="38" height="30" rx="7" fill="var(--sky)" />
    <rect x="18" y="22" width="38" height="30" rx="7" fill="var(--surface)" stroke="var(--ink)" strokeWidth="2.5" />
    <path d="m28 37 5 5 10-11" fill="none" stroke="var(--iris)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const SpotCycle = ({ size = 64 }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
    <circle cx="32" cy="32" r="20" fill="var(--amber-soft)" />
    <path d="M46 26a15 15 0 1 0 1 10" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" />
    <path d="m47 18 0 9-9 0" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    <circle cx="32" cy="32" r="4" fill="var(--iris)" />
  </svg>
);

export const SpotStack = ({ size = 64 }: P) => (
  <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
    <path d="M10 40 32 51l22-11" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M10 31 32 42l22-11" fill="none" stroke="var(--ink)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M32 11 54 22 32 33 10 22Z" fill="var(--iris-soft)" stroke="var(--ink)" strokeWidth="2.5" strokeLinejoin="round" />
  </svg>
);

export const SPOTS = [SpotProjects, SpotCycle, SpotStack];
