import type { CoachAdvice } from "../lib/types";

const PRIORITY_COLORS: Record<CoachAdvice["priority"], string> = {
  Low: "bg-slate-500/30 text-slate-300",
  Med: "bg-apex-accent/30 text-apex-accent",
  High: "bg-apex-red/30 text-red-300",
};

const CATEGORY_ICONS: Record<CoachAdvice["category"], string> = {
  Combat: "⚔",
  Positioning: "⛯",
  Loot: "▦",
  Rotation: "↻",
  Ult: "★",
};

export default function AdviceTicker({ items }: { items: CoachAdvice[] }) {
  if (!items.length) {
    return (
      <div className="rounded-md border border-dashed border-apex-light/40 p-4 text-center text-sm text-slate-500">
        Coach not running. Запусти на странице Coach или Ctrl+Shift+C.
      </div>
    );
  }
  return (
    <ul className="space-y-2">
      {items.map((a, idx) => (
        <li
          key={`${a.at_ms}-${idx}`}
          className="flex gap-3 rounded-md border border-apex-light/40 bg-apex-mid p-3"
        >
          <span className="text-lg leading-none">
            {CATEGORY_ICONS[a.category]}
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm text-white">{a.tip}</div>
            <div className="mt-1 flex items-center gap-2 text-[10px] uppercase tracking-wider text-slate-500">
              <span className={`rounded px-1.5 py-0.5 ${PRIORITY_COLORS[a.priority]}`}>
                {a.priority}
              </span>
              <span>{a.category}</span>
              <span className="ml-auto text-slate-600">
                {new Date(a.at_ms).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
