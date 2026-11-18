"""Error Level Analysis (ELA) and Compression Artifact Inspection."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

from backend.app.config import CASE_DATA_DIR, ELA_HOTSPOT_THRESHOLD

ELA_DIR = CASE_DATA_DIR / "ela_heatmaps"
ELA_DIR.mkdir(parents=True, exist_ok=True)


def compute_ela_heatmap(
    image_path: Path,
    output_heatmap_path: Path,
    quality: int = 90,
    multiplier: float = 15.0,
) -> Tuple[float, Path]:
    """Compute Error Level Analysis (ELA) between original image and a 90%-quality recompression."""
    with Image.open(image_path).convert("RGB") as original:
        # Re-save to in-memory JPEG
        buffer = io.BytesIO()
        original.save(buffer, "JPEG", quality=quality)
        buffer.seek(0)

        with Image.open(buffer) as resaved:
            # Absolute difference
            diff = ImageChops.difference(original, resaved)

            # Amplify differences
            extrema = diff.getextrema()
            max_diff = max([ex[1] for ex in extrema])
            scale = 255.0 / max(max_diff, 1) if max_diff > 0 else 1.0
            scale = min(scale, multiplier)

            enhanced = ImageEnhance.Brightness(diff).enhance(scale)
            enhanced.save(output_heatmap_path, "PNG")

            # Calculate hotspot ratio (pixels with significant difference)
            arr = np.array(diff)
            gray = np.mean(arr, axis=2)
            hotspots = np.sum(gray > 8.0)
            total_pixels = gray.size
            hotspot_ratio = float(hotspots / total_pixels) if total_pixels > 0 else 0.0

            return hotspot_ratio, output_heatmap_path

