"""Pick a hairstyle + hair / eyebrow colours from the photo (front view only).

Measured from MediaPipe's hair class around the detected face: how far hair falls below the chin,
how much hangs beside the face, volume above the forehead. The back of the head is not visible
in a front photo, so "tied back" vs "short" is ambiguous: a gender hint breaks the tie and the
user can always override (photo2vrm --hair / viewer dropdown).
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from . import preprocess

STYLES = ["none", "short02", "short04", "short01", "short03", "bob01", "bob02", "long01", "ponytail01",
          "braid01", "afro01"]
BROW = [70, 63, 105, 66, 107, 336, 296, 334, 293, 300]


def analyse(work: Path, gender_hint: float | None = None) -> dict:
    det = json.load(open(work / "detections.json"))
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    rgb = np.ascontiguousarray(rgba[..., :3])
    cat = preprocess.person_categories(rgb)
    hair = (cat == 1) & (rgba[..., 3] > 127)
    info = {"style": "short02", "reason": "no face", "hair_rgb": None, "brow_rgb": None}
    if not det.get("face"):
        return info
    f = np.array(det["face"])[:, :2]
    x0, x1 = f[:, 0].min(), f[:, 0].max()
    fw = x1 - x0
    top_face, chin = f[10, 1], f[152, 1]
    fh = chin - top_face
    band = np.zeros_like(hair)
    band[:, int(max(0, x0 - 1.2 * fw)):int(x1 + 1.2 * fw)] = True
    hb = hair & band
    area = hb.sum() / max(1.0, fw * fh)
    ys, xs = np.where(hb)
    if area < 0.08 or len(ys) < 50:
        info.update(style="none", reason=f"little hair (area {area:.2f})")
    else:
        below = (ys.max() - chin) / fh
        top_vol = (top_face - ys.min()) / fh
        sides = hb[int(f[33, 1]):int(chin)]
        side_w = (((sides & (np.arange(hair.shape[1]) < x0)).sum(1).max(initial=0) +
                   (sides & (np.arange(hair.shape[1]) > x1)).sum(1).max(initial=0)) / fw)
        m = dict(area=round(float(area), 2), below_chin=round(float(below), 2), top_volume=round(float(top_vol), 2),
                 side_width=round(float(side_w), 2))
        if top_vol > 0.75 and side_w > 0.5:
            style = "afro01"
        elif below > 0.6:
            style = "long01"
        elif below > 0.05 and side_w > 0.12:
            style = "bob02"
        elif gender_hint is not None and gender_hint < 0.5:
            style = "ponytail01"   # close to the head, nothing hanging beside the face: likely tied back
        else:
            style = "short02" if top_vol > 0.4 else "short04"
        info.update(style=style, reason=m)
    px = rgb[hair & (rgba[..., 3] > 200)]
    if len(px) > 50:
        info["hair_rgb"] = np.median(px, 0).tolist()
    # eyebrow colour: darkest third of pixels along the brow landmarks
    pts = f[BROW].astype(np.int32)
    m = np.zeros(hair.shape, np.uint8)
    cv2.polylines(m, [pts[:5]], False, 1, max(2, int(fw * 0.03)))
    cv2.polylines(m, [pts[5:]], False, 1, max(2, int(fw * 0.03)))
    bp = rgb[m > 0]
    if len(bp) > 10:
        lum = bp.sum(1)
        info["brow_rgb"] = np.median(bp[lum <= np.percentile(lum, 15)], 0).tolist()
    return info


def tint_texture(src: Path, rgb, out: Path, strength: float = 1.0) -> Path:
    """Recolour a (greyish/brown) MakeHuman hair texture to rgb, keeping its shading and alpha."""
    im = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
    if im.ndim == 2:
        im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
    if im.shape[2] == 3:
        im = np.dstack([im, np.full(im.shape[:2], 255, np.uint8)])
    lum = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
    a = im[..., 3] > 16
    ref = np.median(lum[a]) if a.any() else 128.0
    shade = np.clip(lum / max(ref, 1.0), 0.3, 1.8)[..., None]
    target = np.array(rgb[::-1], np.float32)  # BGR
    col = np.clip(target * shade, 0, 255)
    out_im = im.copy()
    out_im[..., :3] = (col * strength + im[..., :3] * (1 - strength)).astype(np.uint8)
    cv2.imwrite(str(out), out_im)
    return out
