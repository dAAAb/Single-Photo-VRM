"""Pick shoes (MakeHuman CC0 shoes01–06) from the colour around the photo's feet, or barefoot."""
import json
from pathlib import Path

import cv2
import numpy as np

from . import preprocess
from .proxies import ASSETS

STYLES = {"shoes01": "brown leather", "shoes02": "grey casual", "shoes03": "black boots",
          "shoes04": "black dress", "shoes05": "white sneakers", "shoes06": "blue sneakers"}


def _median_tex(name):
    im = cv2.imread(str(ASSETS / "clothes" / name / f"{name}_diffuse.png"), cv2.IMREAD_UNCHANGED)
    rgb = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float32)
    keep = rgb.sum(1) > 30  # ignore empty atlas space
    return np.median(rgb[keep], 0)


def analyse(work: Path, skin_rgb) -> dict:
    det = json.load(open(work / "detections.json"))
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    k = det.get("keypoints", {})
    ys = np.where(rgba[..., 3] > 127)[0]
    r = max(4, int(0.012 * (ys.max() - ys.min())))
    cat = preprocess.person_categories(np.ascontiguousarray(rgba[..., :3]))
    samples, cats = [], []
    for side in ("left", "right"):
        for name in (f"{side}_big_toe", f"{side}_heel"):
            if name in k and k[name][2] > 0.3:
                x, y = int(k[name][0]), int(k[name][1])
                patch = rgba[max(0, y - r):y + r, max(0, x - r):x + r]
                m = patch[..., 3] > 200
                px = patch[..., :3][m]
                if len(px):
                    samples.append(px)
                    cats.append(cat[max(0, y - r):y + r, max(0, x - r):x + r][m])
    if not samples:
        return {"style": "shoes05", "reason": "feet not detected"}
    px = np.concatenate(samples).astype(np.float32)
    col = np.median(px, 0)
    skin_frac = float(np.isin(np.concatenate(cats), (2, 3)).mean())  # segmenter says bare skin?
    if skin_frac > 0.6:
        return {"style": "none", "reason": f"feet segmented as skin ({skin_frac:.0%})", "rgb": col.tolist()}
    # style from hue / saturation / value (boots only when chosen: a front photo can't judge the shaft)
    h, sat, v = cv2.cvtColor(col.reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_RGB2HSV)[0, 0].astype(float)
    h *= 2  # OpenCV hue is 0..180
    if v > 165 and sat < 60:
        best = "shoes05"          # white / light sneakers
    elif v < 70:
        best = "shoes04"          # black
    elif 190 <= h <= 260 and sat > 60:
        best = "shoes06"          # blue
    elif 10 <= h <= 45 and sat > 80:
        best = "shoes01"          # brown / tan leather
    else:
        best = "shoes02"          # generic casual, recoloured below
    return {"style": best, "reason": f"foot colour {col.round().tolist()} → {STYLES[best]}", "rgb": col.tolist()}
