"""Build the MediaPipe-478 → Anny correspondence automatically: render Anny's neutral face with the
numpy rasterizer, run MediaPipe Face Landmarker on it, and look up triangle + barycentrics per
landmark. Cached in build/models/mp478_anny.npz (anny-full vertex indexing)."""
from pathlib import Path

import anny
import cv2
import numpy as np
import torch

from . import preprocess
from .raster import barycentric, rasterize

CACHE = preprocess.MODELS / "mp478_anny.npz"


def face_colors(model, V, F):
    """Skin, with dark irises/pupils and slightly darker lips so a face detector sees a face."""
    col = np.tile(np.array([[222, 180, 160]], np.float32), (len(F), 1))
    W, I = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    L = list(model.bone_labels)
    for eye in ("eye.L", "eye.R"):
        e = L.index(eye)
        ev = ((I == e) & (W > 0.5)).any(1)
        c = V[ev].mean(0)
        fe = ev[F].all(1)
        v = V[F[fe]].mean(1) - c
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        ang = np.degrees(np.arccos(np.clip(-v[:, 1], -1, 1)))
        col[fe] = np.where(ang[:, None] < 10, [20, 15, 15], np.where(ang[:, None] < 24, [90, 60, 40], [245, 245, 240]))
    return col


def build(force=False):
    if CACHE.exists() and not force:
        return dict(np.load(CACHE))
    model = anny.Anny(topology="anny-full").to(dtype=torch.float32)
    P = torch.eye(4)[None, None].repeat(1, model.bone_count, 1, 1)
    V = model(pose_parameters=P)["vertices"][0].numpy()
    F = np.asarray(model.faces)
    L = list(model.bone_labels)
    W, I = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    hv = ((I == L.index("head")) & (W > 0.5)).any(1)
    center = V[hv].mean(0) + np.array([0, 0, -0.01])
    scale = 512 * 0.62 / np.ptp(V[hv][:, 0])
    rgb, tid, P2 = rasterize(V, F, face_colors(model, V, F), center, scale)
    with preprocess._face_landmarker() as fl:
        r = fl.detect(preprocess._mp_image(rgb))
    if not r.face_landmarks:
        raise RuntimeError("MediaPipe found no face on the Anny render")
    lm = np.array([(p.x * 512, p.y * 512) for p in r.face_landmarks[0]])
    tri, bary, ok = np.zeros((478, 3), np.int32), np.zeros((478, 3), np.float32), np.zeros(478, bool)
    for k, (x, y) in enumerate(lm):
        xi, yi = int(np.clip(x, 0, 511)), int(np.clip(y, 0, 511))
        t = tid[yi, xi]
        if t < 0:  # landmark just off the silhouette: nearest covered pixel
            ys, xs = np.where(tid >= 0)
            j = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
            t, x, y = tid[ys[j], xs[j]], xs[j] + 0.5, ys[j] + 0.5
        tri[k] = F[t]
        bary[k] = np.clip(barycentric((x, y), P2[F[t]]), 0, 1)
        bary[k] /= bary[k].sum()
        ok[k] = True
    vis = rgb.copy()
    for x, y in lm:
        cv2.circle(vis, (int(x), int(y)), 1, (0, 120, 255), -1)
    cv2.imwrite(str(CACHE.with_suffix(".png")), cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
    np.savez(CACHE, tri=tri, bary=bary, ok=ok)
    return {"tri": tri, "bary": bary, "ok": ok}


if __name__ == "__main__":
    c = build(force=True)
    print("correspondences:", int(c["ok"].sum()), "→", CACHE)
