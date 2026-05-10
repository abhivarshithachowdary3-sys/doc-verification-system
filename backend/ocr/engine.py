"""
OCR Engine — wraps Tesseract with image preprocessing optimised for
Indian identity documents (Aadhaar, PAN, Passport, DL).
"""

import re
import logging
from pathlib import Path
from typing import Tuple, Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

from backend.core.config import settings

logger = logging.getLogger(__name__)
pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCREngine:
    """
    Multi-pass OCR engine.
    Pass 1: Standard preprocessing (denoise + threshold)
    Pass 2: Adaptive threshold (catches low-contrast docs)
    Pass 3: Deskewed + sharpened (catches rotated / blurry scans)
    Returns whichever pass yields the highest Tesseract confidence.
    """

    TESSERACT_CONFIG = r"--oem 3 --psm 6 -l eng+hin"

    def __init__(self):
        self._verify_tesseract()

    def _verify_tesseract(self):
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            logger.warning(f"Tesseract not found at {settings.TESSERACT_CMD}: {e}")

    # ── Preprocessing helpers ─────────────────────────────────────────

    def _load_image(self, image_path: str) -> np.ndarray:
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot load image: {image_path}")
        return img

    def _resize(self, img: np.ndarray, target_width: int = 1500) -> np.ndarray:
        h, w = img.shape[:2]
        if w >= target_width:
            return img
        scale = target_width / w
        return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    def _preprocess_standard(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _preprocess_adaptive(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        coords = np.column_stack(np.where(gray > 0))
        if len(coords) < 10:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        h, w = gray.shape
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    def _sharpen(self, img: np.ndarray) -> np.ndarray:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(img, -1, kernel)

    # ── OCR core ─────────────────────────────────────────────────────

    def _run_tesseract(self, processed: np.ndarray) -> Tuple[str, float]:
        pil_img = Image.fromarray(processed)
        data = pytesseract.image_to_data(
            pil_img, config=self.TESSERACT_CONFIG,
            output_type=pytesseract.Output.DICT
        )
        confidences = [c for c in data["conf"] if c != -1]
        mean_conf = float(np.mean(confidences)) if confidences else 0.0
        text = pytesseract.image_to_string(pil_img, config=self.TESSERACT_CONFIG)
        return text.strip(), mean_conf

    def extract(self, image_path: str) -> Tuple[str, float]:
        """
        Main entry point. Returns (raw_text, confidence_score 0–100).
        """
        img = self._load_image(image_path)
        img = self._resize(img)

        results = []

        # Pass 1 — standard
        try:
            p1 = self._preprocess_standard(img)
            t1, c1 = self._run_tesseract(p1)
            results.append((t1, c1))
            logger.debug(f"Pass 1 confidence: {c1:.1f}")
        except Exception as e:
            logger.warning(f"OCR pass 1 failed: {e}")

        # Pass 2 — adaptive
        try:
            p2 = self._preprocess_adaptive(img)
            t2, c2 = self._run_tesseract(p2)
            results.append((t2, c2))
            logger.debug(f"Pass 2 confidence: {c2:.1f}")
        except Exception as e:
            logger.warning(f"OCR pass 2 failed: {e}")

        # Pass 3 — deskew + sharpen
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            p3 = self._sharpen(self._deskew(gray))
            t3, c3 = self._run_tesseract(p3)
            results.append((t3, c3))
            logger.debug(f"Pass 3 confidence: {c3:.1f}")
        except Exception as e:
            logger.warning(f"OCR pass 3 failed: {e}")

        if not results:
            return "", 0.0

        best_text, best_conf = max(results, key=lambda x: x[1])
        return best_text, best_conf


# ── Module-level singleton ────────────────────────────────────────────────────
ocr_engine = OCREngine()
