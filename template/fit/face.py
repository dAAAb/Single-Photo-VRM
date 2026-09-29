"""Fit Anny's face shape (local changes) to MediaPipe's 478 landmarks.

The photo's expression is explained by Anny's own ARKit facial actions, set from MediaPipe's
blendshape scores, so a smile is not baked into the identity. Global phenotype comes from the body fit.
"""
import json
from pathlib import Path

import anny
import cv2
import numpy as np
import roma
import torch

from . import face_corr
from .raster import rasterize

# Ears are not observed by MediaPipe's face mesh, so they are left at the template shape.
FACE_PREFIXES = ("chin-", "eyebrows-", "forehead-", "mouth-", "nose-", "l-eye-", "r-eye-",
                 "l-cheek-", "r-cheek-")
HEAD_EXTRA = ["head-angle-out", "head-fat-incr", "head-back-scale-depth-incr", "head-age-incr"]


def face_labels():
    m = anny.Anny(local_changes="all")
    return [l for l in m.local_change_labels if l.startswith(FACE_PREFIXES)] + HEAD_EXTRA


def fit(work: Path, body_res: dict, iters=(150, 500), verbose=False) -> dict:
    det = json.load(open(work / "detections.json"))
    if det.get("face") is None:
        return {}
    target = torch.tensor(det["face"], dtype=torch.float32)  # (478,3) px; z in px scale, negative = closer
    labels = face_labels()
    model = anny.Anny(topology="anny-full", local_changes=labels, facial_actions="all").to(dtype=torch.float32)
    corr = face_corr.build()
    tri = torch.from_numpy(corr["tri"]).long()
    bary = torch.from_numpy(corr["bary"]).float()
    pheno = {k: float(v) for k, v in body_res["phenotype"].items()}
    shapes = det.get("blendshapes", {})
    fa = torch.tensor([[shapes.get(n, 0.0) for n in model.facial_action_labels]], dtype=torch.float32)
    P = torch.eye(4)[None, None].repeat(1, model.bone_count, 1, 1)

    lc_raw = torch.zeros(len(labels), requires_grad=True)
    pairs = [(labels.index(l), labels.index("r-" + l[2:])) for l in labels if l.startswith("l-") and "r-" + l[2:] in labels]
    pl, pr = torch.tensor([a for a, _ in pairs]), torch.tensor([b for _, b in pairs])
    rv = torch.zeros(3, requires_grad=True)
    fsize = float(np.ptp(target[:, 0].numpy()))
    cam = torch.zeros(3, requires_grad=True)  # log scale, tx, ty (relative)
    tcen = target[:, :2].mean(0)

    def landmarks():
        out = model(pose_parameters=P, phenotype_kwargs=pheno, local_changes_kwargs=torch.tanh(lc_raw)[None],
                    facial_actions=fa)
        V = out["vertices"][0]
        return (V[tri] * bary[..., None]).sum(1), V

    with torch.no_grad():
        X0, _ = landmarks()
        s0 = fsize / float(np.ptp(X0[:, 0].numpy()))

    def project(X):
        Xc = X - X.mean(0)
        Xr = Xc @ roma.rotvec_to_rotmat(rv).T
        s = s0 * torch.exp(cam[0])
        uv = torch.stack([s * Xr[:, 0], -s * Xr[:, 2]], 1) + tcen + cam[1:] * fsize
        return uv, s * Xr[:, 1]

    for stage, n in enumerate(iters):
        opt = torch.optim.Adam([rv, cam] + ([lc_raw] if stage else []), lr=0.02)
        for it in range(n):
            opt.zero_grad()
            X, _ = landmarks()
            uv, z = project(X)
            l2d = ((uv - target[:, :2]) ** 2).sum(1).mean() / fsize ** 2
            zt = target[:, 2] - target[:, 2].mean()
            lz = ((z - z.mean() - zt) ** 2).mean() / fsize ** 2
            lcv = torch.tanh(lc_raw)
            loss = l2d + 0.2 * lz
            if stage:  # small magnitude prior + faces are close to symmetric
                loss = loss + 4e-5 * (lcv ** 2).sum() + 2e-4 * ((lcv[pl] - lcv[pr]) ** 2).sum()
            loss.backward()
            opt.step()
        if verbose:
            print(f"  face stage{stage}: 2d={l2d.item():.6f} z={lz.item():.6f}")

    lc = {l: float(v) for l, v in zip(labels, torch.tanh(lc_raw).detach())}
    json.dump({"local_changes": lc, "err2d": l2d.item(), "errz": lz.item(), "rotvec": rv.tolist()},
              open(work / "face_params.json", "w"), indent=1)
    # QA image: photo crop | fitted landmarks | neutral template vs fitted face renders
    with torch.no_grad():
        X, V = landmarks()
        uv, _ = project(X)
    _qa(work, target.numpy(), uv.numpy(), model, pheno, lc, labels)
    return lc


def _render_face(model, pheno, lc_vals):
    P = torch.eye(4)[None, None].repeat(1, model.bone_count, 1, 1)
    with torch.no_grad():
        V = model(pose_parameters=P, phenotype_kwargs=pheno, local_changes_kwargs=lc_vals).get("vertices")[0].numpy()
    F = np.asarray(model.faces)
    L = list(model.bone_labels)
    W, I = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    hv = ((I == L.index("head")) & (W > 0.5)).any(1)
    rgb, _, _ = rasterize(V, F, face_corr.face_colors(model, V, F), V[hv].mean(0) + np.array([0, 0, -0.01]),
                          400 * 0.62 / np.ptp(V[hv][:, 0]), size=400)
    return rgb


def _qa(work, target, uv, model, pheno, lc, labels):
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    a = rgba[..., 3:4] / 255.0
    img = (rgba[..., :3] * a + 235 * (1 - a)).astype(np.uint8)
    x0, y0 = target[:, :2].min(0)
    x1, y1 = target[:, :2].max(0)
    pad = 0.35 * (x1 - x0)
    X0, Y0, side = int(x0 - pad), int(y0 - pad), int(max(x1 - x0, y1 - y0) + 2 * pad)
    M = np.float32([[400 / side, 0, -X0 * 400 / side], [0, 400 / side, -Y0 * 400 / side]])
    crop = cv2.warpAffine(img, M, (400, 400), borderValue=(235, 235, 235))
    ov = crop.copy()
    for (tx, ty), (px, py) in zip(target[:, :2], uv):
        cv2.circle(ov, (int((tx - X0) * 400 / side), int((ty - Y0) * 400 / side)), 1, (255, 40, 40), -1)
        cv2.circle(ov, (int((px - X0) * 400 / side), int((py - Y0) * 400 / side)), 1, (0, 160, 255), -1)
    neutral = _render_face(model, pheno, None)
    fitted = _render_face(model, pheno, torch.tensor([[lc[l] for l in labels]]))
    sheet = np.concatenate([crop, ov, neutral, fitted], 1)
    for i, t in enumerate(["photo", "landmarks (red) / fit (blue)", "template", "fitted face"]):
        cv2.putText(sheet, t, (i * 400 + 8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 1)
    cv2.imwrite(str(work / "face_fit.png"), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2] / "build" / "fit"
    for name in sys.argv[1:]:
        w = root / name
        body_res = json.load(open(w / "body_params.json"))
        lc = fit(w, body_res, verbose=True)
        top = sorted(lc.items(), key=lambda kv: -abs(kv[1]))[:6]
        print(name, [(k, round(v, 2)) for k, v in top])
