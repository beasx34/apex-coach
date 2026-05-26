import { useEffect, useState } from "react";
import {
  deleteSecret,
  hasSecret,
  loadConfig,
  saveConfig,
  saveSecret,
  testGemini,
} from "../lib/tauri";
import type {
  GameMode,
  GeminiModel,
  Platform,
  SecretName,
  UserConfig,
} from "../lib/types";
import { useAppStore } from "../lib/store";

const PLATFORMS: Platform[] = ["Origin", "Xbl", "Psn", "Switch"];
const MODES: GameMode[] = ["BrPubs", "BrRanked", "Mixtape"];
const MODELS: { value: GeminiModel; label: string; note: string }[] = [
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash", note: "Default — лучший баланс (10 RPM, 250 RPD)" },
  { value: "gemini-2.5-flash-lite", label: "Gemini 2.5 Flash-Lite", note: "Самый быстрый (15 RPM, 1000 RPD)" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro", note: "Умнее всех (5 RPM, 100 RPD)" },
  { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash", note: "Резервный, большой контекст" },
];

function SecretField({
  name,
  label,
  link,
  onSaved,
}: {
  name: SecretName;
  label: string;
  link: string;
  onSaved: () => void;
}) {
  const [value, setValue] = useState("");
  const [stored, setStored] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    hasSecret(name).then(setStored).catch(() => setStored(false));
  }, [name]);

  async function save() {
    if (!value) return;
    setBusy(true);
    setError(null);
    try {
      await saveSecret(name, value);
      setValue("");
      setStored(true);
      onSaved();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    setBusy(true);
    try {
      await deleteSecret(name);
      setStored(false);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-md border border-apex-light/40 bg-apex-mid p-4">
      <div className="mb-2 flex items-center justify-between">
        <label className="text-sm font-semibold">{label}</label>
        <a
          href={link}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-apex-accent hover:underline"
        >
          получить ключ
        </a>
      </div>
      <div className="flex gap-2">
        <input
          type="password"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={stored ? "•••••••••• (сохранён)" : "введи ключ"}
          className="flex-1 rounded-md border border-apex-light/60 bg-apex-dark px-3 py-1.5 text-sm focus:border-apex-accent focus:outline-none"
        />
        <button
          disabled={busy || !value}
          onClick={save}
          className="rounded-md bg-apex-accent px-3 py-1.5 text-sm font-semibold text-black hover:bg-yellow-500 disabled:opacity-40"
        >
          Save
        </button>
        {stored && (
          <button
            disabled={busy}
            onClick={clear}
            className="rounded-md border border-apex-red/60 px-3 py-1.5 text-sm text-red-300 hover:bg-apex-red/20"
          >
            Clear
          </button>
        )}
      </div>
      {error && <div className="mt-2 text-xs text-red-300">{error}</div>}
    </div>
  );
}

export default function Settings() {
  const setConfig = useAppStore((s) => s.setConfig);
  const config = useAppStore((s) => s.config);
  const [draft, setDraft] = useState<UserConfig | null>(config);
  const [saving, setSaving] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(config);
  }, [config]);

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      await saveConfig(draft);
      const fresh = await loadConfig();
      setConfig(fresh);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function ping() {
    setPingResult(null);
    try {
      const r = await testGemini();
      setPingResult(`OK: ${r}`);
    } catch (e) {
      setPingResult(`FAIL: ${e}`);
    }
  }

  if (!draft) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Settings</h2>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Profile
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">In-game name</span>
            <input
              value={draft.player_name}
              onChange={(e) =>
                setDraft({ ...draft, player_name: e.target.value })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Platform</span>
            <select
              value={draft.platform}
              onChange={(e) =>
                setDraft({ ...draft, platform: e.target.value as Platform })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            >
              {PLATFORMS.map((p) => (
                <option key={p}>{p}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Mode</span>
            <select
              value={draft.mode}
              onChange={(e) =>
                setDraft({ ...draft, mode: e.target.value as GameMode })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            >
              {MODES.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Language for tips</span>
            <select
              value={draft.language}
              onChange={(e) => setDraft({ ...draft, language: e.target.value })}
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            >
              <option value="ru">Русский</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          API keys
        </h3>
        <SecretField
          name="gemini_api_key"
          label="Google Gemini API key"
          link="https://aistudio.google.com/app/apikey"
          onSaved={ping}
        />
        <SecretField
          name="tracker_api_key"
          label="Apex tracker API key"
          link="https://portal.apexlegendsapi.com/"
          onSaved={() => {}}
        />
        <div className="flex items-center gap-3">
          <button
            onClick={ping}
            className="rounded-md border border-apex-light/40 px-3 py-1.5 text-sm hover:bg-apex-mid"
          >
            Test Gemini
          </button>
          {pingResult && (
            <span
              className={`text-sm ${
                pingResult.startsWith("OK") ? "text-green-400" : "text-red-300"
              }`}
            >
              {pingResult}
            </span>
          )}
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Coach
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Gemini model</span>
            <select
              value={draft.gemini_model}
              onChange={(e) =>
                setDraft({ ...draft, gemini_model: e.target.value as GeminiModel })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            >
              {MODELS.map((m) => (
                <option key={m.value} value={m.value} title={m.note}>
                  {m.label}
                </option>
              ))}
            </select>
            <span className="text-[10px] text-slate-500">
              {MODELS.find((m) => m.value === draft.gemini_model)?.note}
            </span>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">
              Coach interval (ms) — как часто делать скриншот
            </span>
            <input
              type="number"
              min={500}
              step={100}
              value={draft.coach_interval_ms}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  coach_interval_ms: parseInt(e.target.value, 10) || 1500,
                })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Overlay opacity (0..1)</span>
            <input
              type="number"
              min={0.1}
              max={1}
              step={0.05}
              value={draft.overlay_opacity}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  overlay_opacity: parseFloat(e.target.value) || 0.85,
                })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-400">Tracker provider</span>
            <select
              value={draft.tracker_provider}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  tracker_provider: e.target.value as UserConfig["tracker_provider"],
                })
              }
              className="rounded-md border border-apex-light/60 bg-apex-mid px-3 py-1.5"
            >
              <option value="Mozambique">Mozambiquehe.re (free tier)</option>
              <option value="TrackerGg">Tracker.gg</option>
            </select>
          </label>
        </div>
      </section>

      {error && (
        <div className="rounded-md border border-apex-red/40 bg-apex-red/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div>
        <button
          disabled={saving}
          onClick={save}
          className="rounded-md bg-apex-accent px-4 py-2 text-sm font-semibold text-black hover:bg-yellow-500 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
