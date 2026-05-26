import { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { listen } from "@tauri-apps/api/event";
import "../index.css";
import type { CoachAdvice } from "../lib/types";

const PRIORITY_GLOW: Record<CoachAdvice["priority"], string> = {
  Low: "shadow-[0_0_18px_rgba(255,255,255,0.10)]",
  Med: "shadow-[0_0_24px_rgba(255,183,0,0.45)]",
  High: "shadow-[0_0_28px_rgba(237,28,36,0.65)]",
};

const CATEGORY_ICONS: Record<CoachAdvice["category"], string> = {
  Combat: "⚔",
  Positioning: "⛯",
  Loot: "▦",
  Rotation: "↻",
  Ult: "★",
};

function OverlayApp() {
  const [advice, setAdvice] = useState<CoachAdvice | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    const p = listen<CoachAdvice>("coach://advice", (ev) => {
      setAdvice(ev.payload);
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => setAdvice(null), 6000);
    });
    return () => {
      p.then((u) => u()).catch(() => {});
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!advice) {
    return <div className="h-full w-full" />;
  }

  return (
    <div className="flex h-full w-full items-end justify-end p-3">
      <div
        className={`pointer-events-none flex max-w-sm items-start gap-3 rounded-xl border border-white/15 bg-black/70 px-4 py-3 backdrop-blur-md ${PRIORITY_GLOW[advice.priority]}`}
      >
        <div className="text-2xl leading-none">{CATEGORY_ICONS[advice.category]}</div>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-widest text-slate-400">
            {advice.category} · {advice.priority}
          </div>
          <div className="text-sm font-semibold text-white">{advice.tip}</div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("overlay-root")!).render(<OverlayApp />);
