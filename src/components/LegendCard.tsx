import type { LegendStats } from "../lib/types";

export default function LegendCard({ legend }: { legend: LegendStats }) {
  const winRate = legend.matches
    ? Math.round((legend.wins / legend.matches) * 100)
    : 0;
  return (
    <div className="rounded-lg border border-apex-light/40 bg-apex-mid p-4">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-white">{legend.name}</span>
        <span className="text-xs text-slate-500">{legend.matches} matches</span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
        <div>
          <div className="text-slate-500 text-[10px] uppercase">Kills</div>
          <div className="font-bold">{legend.kills.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-slate-500 text-[10px] uppercase">Damage</div>
          <div className="font-bold">{legend.damage.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-slate-500 text-[10px] uppercase">Win %</div>
          <div className="font-bold text-apex-accent">{winRate}%</div>
        </div>
      </div>
    </div>
  );
}
