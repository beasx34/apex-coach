"""Geometry helper tests."""

from __future__ import annotations

from apex_coach.utils.geometry import FractionalRect, Rect


def test_rect_right_bottom() -> None:
    r = Rect(x=10, y=20, w=100, h=50)
    assert r.right == 110
    assert r.bottom == 70


def test_rect_as_mss_dict() -> None:
    r = Rect(x=1, y=2, w=3, h=4)
    assert r.as_mss_dict() == {"left": 1, "top": 2, "width": 3, "height": 4}


def test_fractional_to_pixels_rounds_correctly() -> None:
    fr = FractionalRect(x=0.1, y=0.2, w=0.3, h=0.4)
    rect = fr.to_pixels(1000, 500)
    assert rect == Rect(x=100, y=100, w=300, h=200)


def test_fractional_to_pixels_full_screen() -> None:
    fr = FractionalRect(x=0.0, y=0.0, w=1.0, h=1.0)
    assert fr.to_pixels(1920, 1080) == Rect(x=0, y=0, w=1920, h=1080)
