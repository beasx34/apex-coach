"""Entry point. Wires capture → vision → state → tactics → AI → overlay together."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
from pathlib import Path
from typing import Any

from apex_coach.ai.coach import AiCoach
from apex_coach.ai.gemini import GeminiClient
from apex_coach.capture.screen import ScreenGrabber
from apex_coach.config.regions import get_preset
from apex_coach.config.settings import Settings
from apex_coach.overlay.hotkeys import HotkeyManager
from apex_coach.overlay.tip_hub import TipHub
from apex_coach.overlay.window import OverlayWindow
from apex_coach.state.aggregator import StateAggregator
from apex_coach.state.events import EventBus
from apex_coach.state.models import GameEvent, GameEventInstance, GameState, SquadState
from apex_coach.tactics.meta import load_meta_notes
from apex_coach.tactics.rules import RulesEngine
from apex_coach.utils.logging import get_logger, setup_logging
from apex_coach.vision.digits import DigitMatcher
from apex_coach.vision.hud_reader import HudReader
from apex_coach.vision.kill_feed import KillFeedReader
from apex_coach.vision.legend_icons import LegendIconMatcher
from apex_coach.vision.minimap import MinimapReader
from apex_coach.vision.ocr import OcrEngine
from apex_coach.vision.squad_panel import SquadPanelReader

_log = get_logger("main")


def _resources_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "resources"


async def _capture_pipeline(
    grabber: ScreenGrabber,
    hud_reader: HudReader,
    kill_reader: KillFeedReader,
    minimap_reader: MinimapReader,
    squad_reader: SquadPanelReader,
    aggregator: StateAggregator,
    ai_coach: AiCoach,
) -> None:
    """Main capture/analyze loop. One coroutine; never returns until cancelled."""
    async for frame in grabber.stream():
        try:
            hud = hud_reader.read(frame.bgra)
            kills = kill_reader.read(frame.bgra)
            mini = minimap_reader.read(frame.bgra)
            squad_result = squad_reader.read(frame.bgra)
            squad = SquadState(members=squad_result.members)
            state = aggregator.update(hud, kill_events=kills, minimap=mini, squad=squad)
            ai_coach.update_state(state)
        except Exception:
            _log.exception("Frame pipeline error")


async def _run_async(settings: Settings, qt_app: Any) -> int:
    """Async coroutine driving the whole app. Returns a process exit code."""
    api_key = settings.resolve_api_key()
    if not api_key:
        _log.error(
            "No Gemini API key in env var %s. Set it before running. See README.",
            settings.ai.api_key_env,
        )
        return 2

    layout = get_preset(settings.layout.preset)
    bus = EventBus()
    hub = TipHub()

    digits = DigitMatcher(_resources_dir() / "digit_templates")
    ocr = OcrEngine()
    hud_reader = HudReader(layout=layout, digits=digits, ocr=ocr)
    kill_reader = KillFeedReader(layout=layout, ocr=ocr)
    minimap_reader = MinimapReader(layout=layout)
    legend_matcher = LegendIconMatcher(_resources_dir() / "legend_icons")
    squad_reader = SquadPanelReader(layout=layout, matcher=legend_matcher)

    grabber = ScreenGrabber(
        monitor=settings.capture.monitor, target_fps=settings.capture.target_fps
    )

    aggregator = StateAggregator(bus=bus)
    rules = RulesEngine(bus=bus, sink=hub)
    gemini = GeminiClient(api_key=api_key, model=settings.ai.model)
    meta_notes = load_meta_notes(_resources_dir())
    ai_coach = AiCoach(
        client=gemini,
        bus=bus,
        sink=hub,
        meta_notes=meta_notes,
        min_interval_s=settings.ai.min_interval_s,
    )

    def _on_legend_detected(_state: GameState, ev: GameEventInstance) -> None:
        payload = ev.payload
        if payload is None:
            return
        slot_s, _, slug = payload.partition(":")
        if slot_s != "0" or not slug:
            return
        _log.info("Local legend detected: %s", slug)
        rules.set_legend(slug)
        ai_coach.set_legend(slug)

    bus.subscribe(GameEvent.LEGEND_DETECTED, _on_legend_detected)

    # PySide6 imports kept local so headless tests don't pay the cost.
    from PySide6.QtWidgets import QApplication

    assert isinstance(qt_app, QApplication)
    window = OverlayWindow(settings.overlay, hub)
    screen = qt_app.primaryScreen()
    if screen is not None:
        geo = screen.geometry()
        window.place_on_screen((geo.x(), geo.y(), geo.width(), geo.height()))
    window.show()

    hotkeys = HotkeyManager(
        settings.hotkeys,
        on_ai_request=ai_coach.request_now,
        on_toggle=window.toggle_visible,
        on_calibrate=lambda: _log.info("Calibration wizard not yet implemented"),
    )
    hotkeys.start()

    capture_task = asyncio.create_task(
        _capture_pipeline(
            grabber,
            hud_reader,
            kill_reader,
            minimap_reader,
            squad_reader,
            aggregator,
            ai_coach,
        )
    )

    # Tie asyncio's loop to Qt's: process Qt events periodically.
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(*_args: object) -> None:
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)
    except NotImplementedError:  # pragma: no cover — Windows event loop
        pass

    async def _qt_pump() -> None:
        while not stop_event.is_set():
            qt_app.processEvents()
            await asyncio.sleep(1 / 60)

    pump_task = asyncio.create_task(_qt_pump())

    await stop_event.wait()
    capture_task.cancel()
    pump_task.cancel()
    for task in (capture_task, pump_task):
        with contextlib.suppress(asyncio.CancelledError):
            await task
    hotkeys.stop()
    grabber.close()
    return 0


def run() -> None:
    """Synchronous entry point declared in ``pyproject.toml``."""
    setup_logging()
    settings = Settings.load()

    # On Linux CI / headless boxes, allow the user to opt into offscreen.
    if (
        "QT_QPA_PLATFORM" not in os.environ
        and sys.platform.startswith("linux")
        and not os.environ.get("DISPLAY")
    ):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)

    rc = asyncio.run(_run_async(settings, app))
    sys.exit(rc)


if __name__ == "__main__":  # pragma: no cover
    run()
