import { useEffect, useState } from "react";
import StatCard from "../components/StatCard";
import LegendCard from "../components/LegendCard";
import { fetchProfile } from "../lib/tauri";
import { useAppStore } from "../lib/store";

export default function Dashboard() {
  const config = useAppStore((s) => s.config);
  const profile = useAppStore((s) => s.profile);
  const setProfile = useAppStore((s) => s.setProfile);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!config?.player_name) return;
    setLoading(true);
    fetchProfile(config.platform, config.player_name)
      .then((p) => {
        setProfile(p);
        setError(null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [config?.player_name, config?.platform, setProfile]);

  if (!config) return <p className="text-slate-500">Loading config…</p>;

  if (!config.player_name) {
    return (
      <div className="rounded-lg border border-dashed border-apex-light/40 p-8 text-center">
        <h2 className="mb-2 text-lg font-semibold">No profile configured</h2>
        <p className="text-sm text-slate-400">
          Открой <span className="text-apex-accent">Settings</span> и укажи свой
          игровой ник + платформу.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">{config.player_name}</h2>
        <p className="text-sm text-slate-500">{config.platform}</p>
      </header>

      {loading && <p className="text-sm text-slate-500">Загружаю профиль…</p>}
      {error && (
        <div className="rounded-md border border-apex-red/40 bg-apex-red/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      {profile && (
        <>
          <section className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Level" value={profile.level} />
            <StatCard
              label="BR rank"
              value={profile.br_rank.division}
              sub={`${profile.br_rank.score} RP`}
              accent
            />
            <StatCard
              label="Selected legend"
              value={profile.selected_legend ?? "—"}
            />
            <StatCard
              label="Tracked legends"
              value={profile.legends.length}
            />
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
              Legends
            </h3>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
              {profile.legends.map((l) => (
                <LegendCard key={l.name} legend={l} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
