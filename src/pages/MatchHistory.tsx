import { useEffect, useState } from "react";
import { fetchMatches } from "../lib/tauri";
import { useAppStore } from "../lib/store";

export default function MatchHistory() {
  const config = useAppStore((s) => s.config);
  const matches = useAppStore((s) => s.matches);
  const setMatches = useAppStore((s) => s.setMatches);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!config?.player_name) return;
    setLoading(true);
    fetchMatches(config.platform, config.player_name)
      .then(setMatches)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [config?.player_name, config?.platform, setMatches]);

  if (!config) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">Match history</h2>

      {!config.player_name && (
        <p className="text-sm text-slate-500">Settings → укажи ник, чтобы видеть матчи.</p>
      )}
      {loading && <p className="text-sm text-slate-500">Загружаю матчи…</p>}
      {error && (
        <div className="rounded-md border border-apex-red/40 bg-apex-red/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {matches.length > 0 && (
        <table className="w-full border-separate border-spacing-y-1 text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="text-left">Legend</th>
              <th className="text-right">Kills</th>
              <th className="text-right">Damage</th>
              <th className="text-right">Place</th>
              <th className="text-right">When</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((m, idx) => (
              <tr
                key={`${m.time_ms}-${idx}`}
                className="bg-apex-mid hover:bg-apex-light/60"
              >
                <td className="rounded-l-md p-2">{m.legend}</td>
                <td className="p-2 text-right font-mono">{m.kills}</td>
                <td className="p-2 text-right font-mono">{m.damage}</td>
                <td className="p-2 text-right font-mono">#{m.placement}</td>
                <td className="rounded-r-md p-2 text-right text-slate-400">
                  {new Date(m.time_ms).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
