"""Transparent, click-through, always-on-top overlay window built on PySide6.

The window does **not** intercept input — :data:`Qt.WindowTransparentForInput`
ensures every click goes through to the game underneath. Hotkeys are handled
separately (:mod:`apex_coach.overlay.hotkeys`).
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from apex_coach.config.settings import OverlaySettings
from apex_coach.overlay.tip_hub import TipHub
from apex_coach.tactics.rules import Tip, TipPriority

_PRIORITY_COLORS: dict[int, str] = {
    TipPriority.INFO: "#7DC4FF",
    TipPriority.SUGGESTION: "#FFE066",
    TipPriority.HIGH: "#FF9F4D",
    TipPriority.CRITICAL: "#FF5252",
}


class TipCard(QWidget):
    """The single tip widget rendered on the screen."""

    def __init__(self, settings: OverlaySettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._tip: Tip | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        self._label.setFont(font)
        self._label.setStyleSheet("color: white;")
        layout.addWidget(self._label)
        self.setLayout(layout)
        self.setMinimumWidth(360)
        self.setMaximumWidth(520)
        self.hide()

    def set_tip(self, tip: Tip | None) -> None:
        self._tip = tip
        if tip is None:
            self.hide()
            return
        self._label.setText(tip.text)
        self.show()
        self.update()

    def paintEvent(self, _event: QPaintEvent) -> None:
        if self._tip is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        bg = QColor(0, 0, 0)
        bg.setAlphaF(self._settings.opacity)
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

        accent = QColor(_PRIORITY_COLORS.get(self._tip.priority, "#FFFFFF"))
        accent.setAlphaF(min(1.0, self._settings.opacity + 0.1))
        painter.setBrush(accent)
        painter.drawRoundedRect(0, 0, 4, self.height(), 2, 2)


class OverlayWindow(QWidget):
    """Top-level transparent overlay window."""

    def __init__(self, settings: OverlaySettings, hub: TipHub) -> None:
        super().__init__()
        self._settings = settings
        self._hub = hub
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._card = TipCard(settings, self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._card)
        self.setLayout(layout)

        hub.set_listener(self._on_tip_changed)

        # Tick the hub so it can expire stale tips even when no new ones come in.
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._hub.tick)
        self._timer.start()

    # ------------------------------------------------------------------
    # placement
    # ------------------------------------------------------------------
    def place_on_screen(self, screen_geometry: tuple[int, int, int, int]) -> None:
        """Position the overlay according to the user's preference.

        ``screen_geometry`` is ``(x, y, width, height)`` of the target monitor.
        """
        sx, sy, sw, sh = screen_geometry
        margin = 24
        ww = 540
        wh = 120
        position = self._settings.position
        if position == "bottom-left":
            x, y = sx + margin, sy + sh - wh - margin
        elif position == "bottom-right":
            x, y = sx + sw - ww - margin, sy + sh - wh - margin
        elif position == "top-left":
            x, y = sx + margin, sy + margin
        else:  # top-right
            x, y = sx + sw - ww - margin, sy + margin
        self.setGeometry(x, y, ww, wh)

    def toggle_visible(self) -> None:
        self.setVisible(not self.isVisible())

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    def _on_tip_changed(self, tip: Tip | None) -> None:
        self._card.set_tip(tip)
