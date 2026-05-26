import { useEffect } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { listen } from "@tauri-apps/api/event";
import Dashboard from "./pages/Dashboard";
import MatchHistory from "./pages/MatchHistory";
import Coach from "./pages/Coach";
import Settings from "./pages/Settings";
import { useAppStore } from "./lib/store";
import type { CoachAdvice } from "./lib/types";
import { loadConfig } from "./lib/tauri";

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? "bg-apex-light text-white"
            : "text-slate-400 hover:bg-apex-mid hover:text-slate-100"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  const setConfig = useAppStore((s) => s.setConfig);
  const pushAdvice = useAppStore((s) => s.pushAdvice);
  const setCoachRunning = useAppStore((s) => s.setCoachRunning);

  useEffect(() => {
    loadConfig()
      .then(setConfig)
      .catch((e) => console.warn("loadConfig failed:", e));

    const adviceUnlistenPromise = listen<CoachAdvice>("coach://advice", (ev) => {
      pushAdvice(ev.payload);
    });
    const statusUnlistenPromise = listen<{ running: boolean }>(
      "coach://status",
      (ev) => setCoachRunning(ev.payload.running),
    );

    return () => {
      adviceUnlistenPromise.then((u) => u()).catch(() => {});
      statusUnlistenPromise.then((u) => u()).catch(() => {});
    };
  }, [setConfig, pushAdvice, setCoachRunning]);

  return (
    <div className="flex h-screen bg-apex-dark text-slate-100">
      <aside className="flex w-56 shrink-0 flex-col gap-1 border-r border-apex-light/40 bg-apex-mid p-4">
        <Link to="/" className="mb-4 block">
          <h1 className="text-xl font-bold tracking-tight">
            <span className="text-apex-red">APEX</span> Coach
          </h1>
          <p className="text-[10px] uppercase tracking-widest text-slate-500">
            real-time tactical AI
          </p>
        </Link>
        <NavItem to="/">Dashboard</NavItem>
        <NavItem to="/matches">Match history</NavItem>
        <NavItem to="/coach">Coach</NavItem>
        <NavItem to="/settings">Settings</NavItem>
        <div className="mt-auto text-[10px] text-slate-500">
          Build {__APP_VERSION__ ?? "0.1.0"}
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/matches" element={<MatchHistory />} />
          <Route path="/coach" element={<Coach />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

declare const __APP_VERSION__: string | undefined;
