import { create } from "zustand";
import type { CoachAdvice, MatchRow, Profile, UserConfig } from "./types";

interface AppState {
  config: UserConfig | null;
  profile: Profile | null;
  matches: MatchRow[];
  coachRunning: boolean;
  advice: CoachAdvice[];
  setConfig: (c: UserConfig) => void;
  setProfile: (p: Profile | null) => void;
  setMatches: (m: MatchRow[]) => void;
  setCoachRunning: (running: boolean) => void;
  pushAdvice: (a: CoachAdvice) => void;
  clearAdvice: () => void;
}

const ADVICE_BUFFER = 20;

export const useAppStore = create<AppState>((set) => ({
  config: null,
  profile: null,
  matches: [],
  coachRunning: false,
  advice: [],
  setConfig: (c) => set({ config: c }),
  setProfile: (p) => set({ profile: p }),
  setMatches: (m) => set({ matches: m }),
  setCoachRunning: (running) => set({ coachRunning: running }),
  pushAdvice: (a) =>
    set((s) => ({ advice: [a, ...s.advice].slice(0, ADVICE_BUFFER) })),
  clearAdvice: () => set({ advice: [] }),
}));
