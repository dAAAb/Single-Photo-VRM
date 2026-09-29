"""OPTIONAL AI turnaround: FLUX.2-klein-4B (mflux, MLX on Apple Silicon) turns the photo into a
front / side / back T-pose sheet; the body is then fitted to all three silhouettes (the side view
constrains depth: chest, belly, seat) and the texture is baked from whichever view faces each texel.

Opt-in only (photo2vrm --ai-turnaround / viewer checkbox); first use downloads ~15 GB.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import anny
import cv2
import numpy as np
import roma
import torch

from . import backview, body, preprocess

PROMPT = ("Character turnaround sheet for game design of exactly this person: three full-body views side by "
          "side on a plain white background — front view, side view (profile facing left), and back view. "
          "Same person, same face, same hairstyle and hair colour, same clothes and shoes in every view. "
          "Remove glasses and any facial accessories. T-pose with arms straight out horizontally, feet "
          "slightly apart, neutral expression, even studio lighting, no shadows, no text.")
VIEW_NAMES = ("front", "side", "back")
SIZE = preprocess.SIZE
MARGIN = preprocess.MARGIN


def generate(work: Path, seed: int = 7, log=print) -> Path:
    backview.ensure(log)
    rgba = cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED)
    a = rgba[..., 3:4].astype(np.float32) / 255
    cv2.imwrite(str(work / "front_white.png"), (rgba[..., :3] * a + 255 * (1 - a)).astype(np.uint8))
    out = work / "turnaround_raw.png"
    log("    FLUX.2-klein-4B turnaround sheet (MLX; first use downloads ~15 GB)")
    subprocess.run([str(backview.CLI), "--model", backview.MODEL, "--image-paths", str(work / "front_white.png"),
                    "--prompt", PROMPT, "--steps", "4", "--seed", str(seed), "--width", "1536", "--height", "1024",
                    "--quantize", "8", "--output", str(out)], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.PIPE)
    return out


def split(sheet_path: Path, work: Path) -> dict:
    """Segment the three figures, normalise them with ONE common scale (same sheet → same pixel
    scale), feet on a common baseline. Returns per-view info; raises if it isn't three figures."""
    rgb = cv2.cvtColor(cv2.imread(str(sheet_path)), cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    diff = np.linalg.norm(rgb.astype(np.float32) - 255, axis=2)
    cat = preprocess.person_categories(rgb)
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    gc[(diff > 30) | (cat > 0)] = cv2.GC_PR_FGD
    gc[cv2.erode(((diff > 60) & (cat > 0)).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0] = cv2.GC_FGD
    gc[:4], gc[-4:], gc[:, :4], gc[:, -4:] = cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), gc, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    m = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    comps = sorted(range(1, n), key=lambda i: -stats[i, cv2.CC_STAT_AREA])[:3]
    if len(comps) < 3 or stats[comps[2], cv2.CC_STAT_AREA] < 0.2 * stats[comps[0], cv2.CC_STAT_AREA]:
        raise RuntimeError(f"expected 3 figures on the sheet, found {len(comps)} usable")
    comps.sort(key=lambda i: stats[i, cv2.CC_STAT_LEFT])
    boxes = [stats[i, :4] for i in comps]
    extent = max(max(b[2], b[3]) for b in boxes)
    s = SIZE * (1 - 2 * MARGIN) / extent
    base = max(b[1] + b[3] for b in boxes)
    views = {}
    (work / "views").mkdir(exist_ok=True)
    for name, i, (x, y, bw, bh) in zip(VIEW_NAMES, comps, boxes):
        mask = (lab == i)
        cx = x + bw / 2
        M = np.float32([[s, 0, SIZE / 2 - s * cx], [0, s, SIZE * (1 - MARGIN) - s * base]])
        rgba = np.dstack([rgb, (mask * 255).astype(np.uint8)])
        out = cv2.warpAffine(rgba, M, (SIZE, SIZE), flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0))
        cv2.imwrite(str(work / "views" / f"{name}.png"), cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
        views[name] = {"path": str(work / "views" / f"{name}.png")}
    # which way does the side view face? (nose vs ears from the pose landmarker)
    side = cv2.cvtColor(cv2.imread(views["side"]["path"], cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    kps, _, _ = preprocess.detect(side)
    ears = [kps[k][0] for k in ("left_ear", "right_ear") if k in kps and kps[k][2] > 0.2]
    facing_left = True
    if "nose" in kps and ears:
        facing_left = kps["nose"][0] < float(np.mean(ears))
    # Anny faces -Y; rotation about +Z by yaw maps forward to image x = sin(yaw)
    views["front"]["yaw"], views["back"]["yaw"] = 0.0, float(np.pi)
    views["side"]["yaw"] = -np.pi / 2 if facing_left else np.pi / 2
    front = cv2.cvtColor(cv2.imread(views["front"]["path"], cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    views["front"]["keypoints"], _, _ = preprocess.detect(front)
    json.dump(views, open(work / "views.json", "w"), indent=1)
    return views


def _rotz(yaw):
    c, s_ = np.cos(yaw), np.sin(yaw)
    return torch.tensor([[c, -s_, 0], [s_, c, 0], [0, 0, 1]], dtype=torch.float32)


def fit(work: Path, views: dict, gender_init=0.5, iters=(200, 350)) -> dict:
    """Shared shape + T-pose, shared camera scale, per-view translation; all three silhouettes."""
    model = body.build_model()
    kps = views["front"].get("keypoints", {})
    labels = list(kps)
    f = body.Fitter(model, labels or ["nose"])
    rv_t = body.tpose_rotvecs(model)
    with torch.no_grad():
        f.rv.copy_(rv_t)
        f.pheno_raw[list(model.phenotype_labels).index("gender")] = float(np.log(gender_init / (1 - gender_init)))
    obs = torch.tensor([[kps[k][0], kps[k][1]] for k in labels], dtype=torch.float32) if labels else None
    vis = torch.tensor([kps[k][2] for k in labels], dtype=torch.float32) if labels else None
    data = []
    for name in VIEW_NAMES:
        rgba = cv2.imread(views[name]["path"], cv2.IMREAD_UNCHANGED)
        mask = rgba[..., 3] > 127
        ys, xs = np.where(mask)
        dt = torch.from_numpy(cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32))[None, None]
        cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cont = np.concatenate([c[:, 0] for c in cnts]).astype(np.float32)
        cont = torch.from_numpy(cont[np.linspace(0, len(cont) - 1, 600).astype(int)])
        data.append(dict(name=name, R=_rotz(views[name]["yaw"]), dt=dt, contour=cont,
                         t0=torch.tensor([float((xs.min() + xs.max()) / 2), float(ys.min() + 0.47 * (ys.max() - ys.min()))]),
                         h=float(ys.max() - ys.min())))
    person_h = data[0]["h"]
    s0 = person_h / 1.70
    trans = torch.zeros(len(data), 2, requires_grad=True)
    # AI sheets are not pose-consistent between views (e.g. arms raised in front, hanging in the side
    # view): each view gets its own arm offsets on top of the shared body pose.
    ARM = ["clavicle.L", "clavicle.R", "upperarm01.L", "upperarm01.R", "lowerarm01.L", "lowerarm01.R"]
    arm_idx = [body.POSE_BONES.index(b) for b in ARM]
    arm_off = torch.zeros(len(data), len(ARM), 3, requires_grad=True)
    sub = torch.arange(0, model.template_vertices.shape[0], 3)

    def forward():
        """One batched Anny evaluation: shared shape/pose, per-view arm offsets."""
        n = len(data)
        rv = f.rv[None].repeat(n, 1, 1).clone()
        rv[:, arm_idx] = rv[:, arm_idx] + arm_off
        pose = torch.eye(4).repeat(n, f.B, 1, 1).clone()
        pose[:, f.bone_idx, :3, :3] = roma.rotvec_to_rotmat(rv)
        out = model(pose_parameters=pose, phenotype_kwargs=f.pheno()[None].repeat(n, 1),
                    local_changes_kwargs=f.lc()[None].repeat(n, 1))
        return out, out["vertices"]

    def project(X, d, k):
        Xr = X @ d["R"].T
        s = s0 * torch.exp(f.cam[0])
        return torch.stack([s * Xr[:, 0] + d["t0"][0] + trans[k, 0] * s0, -s * Xr[:, 2] + d["t0"][1] + trans[k, 1] * s0], 1)

    def sample(dt, p):
        H, W = dt.shape[-2:]
        g = torch.stack([p[:, 0] / (W - 1) * 2 - 1, p[:, 1] / (H - 1) * 2 - 1], 1)[None, None]
        return torch.nn.functional.grid_sample(dt, g, align_corners=True)[0, 0, 0]

    log = {}
    for stage, n in enumerate(iters):
        params = [f.cam, trans, f.rv] + ([f.pheno_raw, f.lc_raw] if stage else [])
        params = params + [arm_off]
        opt = torch.optim.Adam(params, lr=0.03 if stage == 0 else 0.02)
        for it in range(n):
            opt.zero_grad()
            out, Vs = forward()
            loss = 0.0
            if obs is not None:
                pk = project(f.kpr({"vertices": Vs[:1]})[0], data[0], 0)
                r2 = ((pk - obs) ** 2).sum(1)
                loss = loss + 10 * (vis * body.gmof(r2, (0.04 * person_h) ** 2)).sum() / (vis.sum() * person_h ** 2)
            for k, d in enumerate(data):
                pv = project(Vs[k][sub], d, k)
                l_in = (sample(d["dt"], pv) / person_h).pow(2).mean()
                dd = torch.cdist(d["contour"], pv).min(1).values / person_h
                # clothes are looser than the body: the silhouette may stand ~1.5% of the height off
                l_cov = body.gmof(torch.relu(dd - 0.015) ** 2, 0.03 ** 2).mean()
                loss = loss + 20 * l_in + (5 if stage else 3) * l_cov
                log[d["name"]] = (float(l_in.detach()), float(l_cov.detach()))
            loss = loss + 5e-3 * ((f.rv - rv_t) ** 2).sum() + 2e-3 * (arm_off ** 2).sum()
            if stage:
                loss = loss + 1e-3 * ((f.pheno() - 0.5) ** 2).sum() + 5e-4 * (f.lc() ** 2).sum()
            loss.backward()
            opt.step()
    s = float(s0 * torch.exp(f.cam[0]))
    res = {
        "loss": float(loss.detach()), "stylized": False, "kp_error": 0.0, "inside": 0.0, "coverage": 0.0,
        "multiview": {d["name"]: {"yaw": views[d["name"]]["yaw"], "scale": s,
                                  "tx": float(d["t0"][0] + trans[k, 0] * s0), "ty": float(d["t0"][1] + trans[k, 1] * s0),
                                  "inside": log[d["name"]][0], "coverage": log[d["name"]][1],
                                  "arm_rotvec": {b: arm_off[k, j].tolist() for j, b in enumerate(ARM)}}
                      for k, d in enumerate(data)},
        "phenotype": {k: float(v) for k, v in zip(model.phenotype_labels, f.pheno().detach())},
        "local_changes": {k: float(v) for k, v in zip(model.local_change_labels, f.lc().detach())},
        "pose_rotvec": {b: f.rv[i].tolist() for i, b in enumerate(body.POSE_BONES)},
        "bone_scale": {},
    }
    json.dump(res, open(work / "multiview_params.json", "w"), indent=1)
    return res


def hair_style_from_views(work: Path) -> tuple[str | None, str]:
    """What the front photo can't show: hanging hair (back view) and a bun (side view)."""
    vj = work / "views.json"
    if not vj.exists():
        return None, "no views"
    views = json.load(open(vj))

    def hair_mask(name):
        rgba = cv2.cvtColor(cv2.imread(views[name]["path"], cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        cat = preprocess.person_categories(np.ascontiguousarray(rgba[..., :3]))
        ys = np.where(rgba[..., 3] > 127)[0]
        return (cat == 1) & (rgba[..., 3] > 127), ys.min(), ys.max() - ys.min()

    def row_extent(m, y):
        xs = np.where(m[int(y)])[0]
        return (xs.min(), xs.max()) if len(xs) else None

    back, top, H = hair_mask("back")
    if back.sum() < 200:
        return None, "no hair in back view"
    head_w = max((np.ptp(e) for e in (row_extent(back, top + f * H) for f in np.arange(0.02, 0.1, 0.01)) if e), default=1)
    below = back[int(top + 0.17 * H):]
    rows = np.where(below.any(1))[0]
    if len(rows) > 0.02 * H:  # hair hangs below the neck
        width = np.median([np.ptp(np.where(below[r])[0]) for r in rows])
        style = "ponytail01" if width < 0.45 * head_w else "long01"
        return style, f"back view: hair hangs below the neck (width {width / head_w:.2f} of head)"
    side, stop, sH = hair_mask("side")
    back_dir = 1 if views["side"]["yaw"] < 0 else -1  # facing left → the back of the head is +x
    def back_edge(f0, f1):
        vals = [e[1] if back_dir > 0 else -e[0] for e in (row_extent(side, stop + f * sH) for f in np.arange(f0, f1, 0.01)) if e]
        return max(vals) if vals else None
    upper, lower = back_edge(0.02, 0.06), back_edge(0.07, 0.13)
    if upper is not None and lower is not None and lower - upper > 0.12 * head_w:
        return "rehmanpolanski_hair_bun_brown", f"side view: bun sticks out {(lower - upper) / head_w:.2f} head widths"
    return None, "nothing extra seen from the back/side"
