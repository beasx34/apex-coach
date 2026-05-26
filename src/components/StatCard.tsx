interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}

export default function StatCard({ label, value, sub, accent }: StatCardProps) {
  return (
    <div
      className={`rounded-lg border border-apex-light/40 bg-apex-mid p-4 ${
        accent ? "ring-1 ring-apex-red/40" : ""
      }`}
    >
      <div className="text-xs uppercase tracking-widest text-slate-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-slate-400">{sub}</div>}
    </div>
  );
}
