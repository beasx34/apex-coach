import { invoke } from "@tauri-apps/api/core";
import type {
  CoachAdvice,
  MatchRow,
  Platform,
  Profile,
  SecretName,
  UserConfig,
} from "./types";

export async function loadConfig(): Promise<UserConfig> {
  return invoke<UserConfig>("load_config");
}

export async function saveConfig(cfg: UserConfig): Promise<void> {
  await invoke("save_config", { cfg });
}

export async function saveSecret(name: SecretName, value: string): Promise<void> {
  await invoke("save_secret", { name, value });
}

export async function hasSecret(name: SecretName): Promise<boolean> {
  return invoke<boolean>("has_secret", { name });
}

export async function deleteSecret(name: SecretName): Promise<void> {
  await invoke("delete_secret", { name });
}

export async function fetchProfile(
  platform: Platform,
  name: string,
): Promise<Profile> {
  return invoke<Profile>("fetch_profile", { platform, name });
}

export async function fetchMatches(
  platform: Platform,
  name: string,
): Promise<MatchRow[]> {
  return invoke<MatchRow[]>("fetch_match_history", { platform, name });
}

export async function testGemini(): Promise<string> {
  return invoke<string>("test_gemini");
}

export async function previewCoach(): Promise<CoachAdvice> {
  return invoke<CoachAdvice>("preview_coach");
}

export async function startCoach(): Promise<void> {
  await invoke("start_coach");
}

export async function stopCoach(): Promise<void> {
  await invoke("stop_coach");
}

export async function openOverlay(): Promise<void> {
  await invoke("open_overlay");
}

export async function closeOverlay(): Promise<void> {
  await invoke("close_overlay");
}

export async function setOverlayClickThrough(on: boolean): Promise<void> {
  await invoke("set_overlay_click_through", { on });
}
