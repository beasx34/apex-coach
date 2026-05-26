# Apex Coach

Real-time Apex Legends tactical coach for Windows. Captures your HUD via OCR,
builds a live game-state context, and asks **Google Gemini** for a single
actionable tip that appears in a transparent overlay window on top of the game.

> Heads-up: EA / Respawn does not expose a public live-match API for Apex
> Legends. Apex Coach therefore relies on **screen-capture + OCR of the HUD**
> for "real-time" data. Profile / match-history stats come from third-party
> tracker APIs (Mozambiquehe.re by default, Tracker.gg optional).
>
> No game memory is read, no DLL is injected — Apex Coach only reads pixels
> from your monitor, like Mobalytics / Outplayed.

## Features

- **Dashboard** — profile, level, BR rank, per-legend stats
- **Match history** — recent matches (where the tracker plan allows it)
- **Coach** — Tokio loop captures the screen, OCRs the HUD, and asks Gemini
  for a short tactical tip when context meaningfully changes (new kill, ammo
  drops below 5, squad count drops, ring phase changes, +200 damage)
- **Overlay window** — transparent, always-on-top, click-through, shows the
  latest tip with a category icon and priority glow
- **Global hotkeys** — `Ctrl+Shift+C` toggle coach, `Ctrl+Shift+O` toggle
  overlay, `Ctrl+Shift+P` pause emissions
- **Secrets in Windows Credential Manager** via `keyring` — API keys never
  touch disk in plaintext

## Quick start

### Prerequisites (Windows 10/11)

1. [Node.js 22+](https://nodejs.org) and [pnpm 9+](https://pnpm.io/installation)
2. [Rust stable](https://rustup.rs/) (`rustup default stable`)
3. [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   with the "Desktop development with C++" workload
4. [WebView2 runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
   (already installed on Windows 11)

### API keys

| Key | Where to get it | Notes |
|----|----|----|
| **Gemini API** | <https://aistudio.google.com/app/apikey> | Free tier, ~30 sec to create |
| **Apex tracker API** (Mozambique) | <https://portal.apexlegendsapi.com/> | Free tier, requires their Discord |
| Apex tracker API (Tracker.gg, optional) | <https://tracker.gg/developers> | Application-only |

You paste both keys into the in-app **Settings** screen — they are stored in
Windows Credential Manager via the `keyring` crate, never in a file.

### Develop

```powershell
git clone https://github.com/beasx34/apex-coach
cd apex-coach
pnpm install
pnpm tauri dev
```

### Build a release installer

```powershell
pnpm tauri build
```

Artifacts: `src-tauri/target/release/bundle/{msi,nsis}/`.

## Configuration

`%APPDATA%/ai.apexcoach.app/config.toml` — written by the **Settings** page.

Tunable knobs:

- `coach_interval_ms` — how often the OCR loop fires (default `1500`)
- `gemini_model` — `gemini-2.5-flash` (default), `gemini-2.5-flash-lite`,
  `gemini-2.5-pro`, `gemini-2.0-flash`
- `language` — `ru` or `en` for tip language
- `rois` — pixel rectangles for ammo / squads / kills / damage / ring HUD.
  Defaults assume 1920×1080; the in-app **Coach** page will gain a visual ROI
  editor in a follow-up PR.
- `tracker_provider` — `Mozambique` (default) or `TrackerGg`

## How the real-time loop works

```
                  ┌─────────────────────────────┐
                  │  Tokio task (coach::start)  │
   sleep(interval)│                             │
        │         │  capture::capture_primary() │
        ▼         │            │                │
                  │            ▼                │
                  │   crop ROIs + OCR (each)    │
                  │            │                │
                  │            ▼                │
                  │  game_state::parse_from_… ──┼──► GameContext { ammo, … }
                  │            │                │
                  │  meaningful_change?  no ────┼──► skip
                  │            │ yes            │
                  │            ▼                │
                  │  gemini::coach(ctx, prof.)  │
                  │            │                │
                  │            ▼                │
                  │  app.emit("coach://advice") ┼──► Overlay window
                  └─────────────────────────────┘
```

## CI

`.github/workflows/ci.yml` runs three jobs:

1. **frontend** (ubuntu) — `pnpm lint`, `pnpm typecheck`, `pnpm build`
2. **rust-check** (ubuntu) — `cargo fmt --check`, `cargo clippy -D warnings`,
   `cargo test`. Windows-only code paths are gated behind `#[cfg(windows)]`.
3. **windows-build** (windows-latest) — `pnpm tauri build`, uploads MSI/NSIS
   installer as an artifact.

## EA Terms of Service

This tool does not modify the game, does not read game memory, and does not
inject any code into the Apex Legends process. It is functionally equivalent
to a streamer dashboard / Mobalytics-style overlay. Use at your own risk; EA
has not officially endorsed any third-party overlay.

## License

[MIT](./LICENSE) © 2026 beasx34
