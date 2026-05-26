import { useState } from "react";
import AdviceTicker from "../components/AdviceTicker";
import {
  openOverlay,
  closeOverlay,
  previewCoach,
  startCoach,
  stopCoach,
} from "../lib/tauri";
import { useAppStore } from "../lib/store";

export default function Coach() {
  const coachRunning = useAppStore((s) => s.coachRunning);
  const advice = useAppStore((s) => s.advice);
  const pushAdvice = useAppStore((s) => s.pushAdvice);
  const clearAdvice = useAppStore((s) => s.clearAdvice);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      if (coachRunning) {
        await stopCoach();
        await closeOverlay();
      } else {
        await openOverlay();
        await startCoach();
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function preview() {
    setError(null);
    try {
      const tip = await previewCoach();
      pushAdvice(tip);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Real-time coach</h2>
          <p className="text-sm text-slate-500">
            OCR HUD → Gemini → советы в оверлей поверх игры.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            disabled={busy}
            onClick={preview}
            className="rounded-md border border-apex-light/40 px-3 py-1.5 text-sm hover:bg-apex-mid"
          >
            Preview tip
          </button>
          <button
            disabled={busy}
            onClick={toggle}
            className={`rounded-md px-4 py-1.5 text-sm font-semibold ${
              coachRunning
                ? "bg-apex-red text-white hover:bg-red-700"
                : "bg-apex-accent text-black hover:bg-yellow-500"
            }`}
          >
            {coachRunning ? "Stop coach" : "Start coach"}
          </button>
        </div>
      </header>

      {error && (
        <div className="rounded-md border border-apex-red/40 bg-apex-red/10 p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            Live feed
          </h3>
          <button
            onClick={clearAdvice}
            className="text-xs text-slate-500 hover:text-slate-300"
          >
            clear
          </button>
        </div>
        <AdviceTicker items={advice} />
      </section>

      <section className="rounded-md border border-apex-light/40 bg-apex-mid p-4 text-xs text-slate-400">
        <h4 className="mb-2 text-sm font-semibold text-slate-200">Hotkeys</h4>
        <ul className="space-y-1">
          <li><code className="text-apex-accent">Ctrl+Shift+C</code> — toggle coach</li>
          <li><code className="text-apex-accent">Ctrl+Shift+O</code> — toggle overlay</li>
          <li><code className="text-apex-accent">Ctrl+Shift+P</code> — pause/resume</li>
        </ul>
      </section>
    </div>
  );
}
