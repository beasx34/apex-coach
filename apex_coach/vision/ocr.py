"""General-purpose OCR wrapper around RapidOCR ONNX.

RapidOCR ships with self-contained ONNX models — no system tesseract required.
Lazy initialization avoids paying the ~500 MB model load cost during tests
that don't touch text recognition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from apex_coach.utils.logging import get_logger

_log = get_logger("ocr")


@dataclass(frozen=True, slots=True)
class OcrResult:
    """One recognized text region."""

    text: str
    confidence: float


class _RapidOcrLike(Protocol):
    def __call__(
        self, image: np.ndarray
    ) -> tuple[list[tuple[list[list[int]], str, float]] | None, float | None]: ...


class OcrEngine:
    """Wraps :class:`rapidocr_onnxruntime.RapidOCR`.

    Methods are safe to call from any thread but not reentrant on the same
    instance — create one per worker thread if you need parallelism.
    """

    def __init__(self) -> None:
        self._impl: _RapidOcrLike | None = None

    def _ensure(self) -> _RapidOcrLike:
        if self._impl is None:
            from rapidocr_onnxruntime import RapidOCR

            _log.info("Loading RapidOCR ONNX models (first-time only)")
            self._impl = RapidOCR()
        return self._impl

    def read_text(self, image: np.ndarray) -> list[OcrResult]:
        """Run OCR on a single image. Returns one result per recognized box."""
        impl = self._ensure()
        result, _elapsed = impl(image)
        if not result:
            return []
        return [OcrResult(text=str(text), confidence=float(conf)) for _box, text, conf in result]

    def read_first_text(self, image: np.ndarray, *, min_confidence: float = 0.5) -> str | None:
        """Convenience: return the most-confident text or ``None``."""
        candidates = [r for r in self.read_text(image) if r.confidence >= min_confidence]
        if not candidates:
            return None
        candidates.sort(key=lambda r: r.confidence, reverse=True)
        return candidates[0].text
