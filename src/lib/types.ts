export type Platform = "Origin" | "Xbl" | "Psn" | "Switch";
export type GameMode = "BrPubs" | "BrRanked" | "Mixtape";
export type OcrEngineChoice = "WindowsOcr" | "None";
export type OverlayCorner = "TopLeft" | "TopRight" | "BottomLeft" | "BottomRight";

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface HudRois {
  ammo: Rect;
  squads_left: Rect;
  kills: Rect;
  damage: Rect;
  ring_timer: Rect;
}

export interface OverlayPos {
  corner: OverlayCorner;
  offset_x: number;
  offset_y: number;
}

export interface HotkeyConfig {
  toggle_coach: string;
  toggle_overlay: string;
  pause_emit: string;
}

export type GeminiModel =
  | "gemini-2.5-flash"
  | "gemini-2.5-flash-lite"
  | "gemini-2.5-pro"
  | "gemini-2.0-flash";

export interface UserConfig {
  player_name: string;
  platform: Platform;
  mode: GameMode;
  coach_interval_ms: number;
  overlay_opacity: number;
  overlay_position: OverlayPos;
  hotkeys: HotkeyConfig;
  ocr_engine: OcrEngineChoice;
  rois: HudRois;
  language: string;
  gemini_model: GeminiModel;
  tracker_provider: "Mozambique" | "TrackerGg";
}

export interface RankInfo {
  division: string;
  score: number;
  percentile: number | null;
}

export interface LegendStats {
  name: string;
  kills: number;
  damage: number;
  wins: number;
  matches: number;
}

export interface Profile {
  platform: Platform;
  display_name: string;
  level: number;
  br_rank: RankInfo;
  legends: LegendStats[];
  selected_legend: string | null;
}

export interface MatchRow {
  legend: string;
  kills: number;
  damage: number;
  placement: number;
  time_ms: number;
}

export type Priority = "Low" | "Med" | "High";
export type Category = "Combat" | "Positioning" | "Loot" | "Rotation" | "Ult";

export interface CoachAdvice {
  tip: string;
  priority: Priority;
  category: Category;
  at_ms: number;
}

export type SecretName = "tracker_api_key" | "gemini_api_key";
