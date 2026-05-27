"""Pytest configuration.

Forces Qt to use the offscreen platform so importing ``PySide6.QtWidgets`` in
the test runner doesn't need a real display server.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
