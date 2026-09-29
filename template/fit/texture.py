"""Bake a UV texture for the fitted Anny mesh from the (single) photo.

For every texel: back-project to the posed mesh surface, then
  visible in the photo            → photo colour
  hidden, but the view ray lands on the same body part (e.g. the back of the torso)
                                  → photo colour at the same (x, z)  ("front-to-back" fill)
  back of the head                → hair colour (or skin when no hair was segmented)
  otherwise (other part in front, outside the silhouette)
                                  → inpainted in UV space from valid neighbours.
The head is aligned with a least-squares 2D affine from the 478 face landmarks.
"""
from __future__ import annotations

import json
from pathlib import Path

import anny
import cv2
import numpy as np
import roma
import torch

from . import body, face, face_corr, preprocess
from .raster import rasterize

PARTS = {  # coarse body part per bone prefix (used to reject front-to-back fills through another part)
    "head": ("head", "eye", "neck"), "torso": ("root", "spine", "pelvis", "clavicle", "breast"),
    "arm_L": ("shoulder01.L", "upperarm", "lowerarm", "wrist.L", "finger", "metacarpal"),
    "leg_L": ("upperleg", "lowerleg", "foot", "toe"),
}


def part_of(label: str) -> str:
    side = label.rsplit(".", 1)[-1] if "." in label else ""
    for part, prefixes in PARTS.items():
        if label.startswith(prefixes):
            if part in ("arm_L", "leg_L"):
                return part[:-1] + (side or "L")
            return part
    return "torso"


def posed_mesh(work: Path, params: dict, body_res: dict):
    """The final-shape anny-full mesh in the photo's pose and camera (plus the photo's expression)."""
    det = json.load(open(work / "detections.json"))
    lcs = params["local_changes"]
    model = anny.Anny(topology="anny-full", local_changes=list(lcs), facial_actions="all").to(dtype=torch.float32)
    L = list(model.bone_labels)
    pose = torch.eye(4).repeat(1, model.bone_count, 1, 1)
    for b, rv in body_res["pose_rotvec"].items():
        pose[0, L.index(b), :3, :3] = roma.rotvec_to_rotmat(torch.tensor(rv))
    for b, sc in (params.get("bone_scale") or {}).items():
        pose[0, L.index(b), :3, :3] *= sc
    shapes = det.get("blendshapes", {})
    fa = torch.tensor([[shapes.get(n, 0.0) for n in model.facial_action_labels]])
    with torch.no_grad():
        V = model(pose_parameters=pose, phenotype_kwargs=params["phenotype"], local_changes_kwargs=lcs,
                  facial_actions=fa)["vertices"][0].numpy()
    c = body_res["camera"]
    s, s0, cam, t0 = c["scale"], c["s0"], c["cam"], c["t0"]
    tx, ty = t0[0] + cam[1] * s0, t0[1] + cam[2] * s0
    P = np.stack([s * V[:, 0] + tx, -s * V[:, 2] + ty], 1)
    return model, V, P, s, (tx, ty), det


def align_head(model, V, P, det):
    """Warp the projected head vertices so Anny's landmarks land on the detected ones."""
    if not det.get("face"):
        return P
    corr = face_corr.build()
    proj = (P[corr["tri"]] * corr["bary"][..., None]).sum(1)
    target = np.array(det["face"])[:, :2]
    A = np.c_[proj, np.ones(len(proj))]
    M, *_ = np.linalg.lstsq(A, target, rcond=None)  # 3x2 affine
    L = list(model.bone_labels)
    W, I = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    head_ids = [L.index(b) for b in ("head", "eye.L", "eye.R")]
    wh = (W * np.isin(I, head_ids)).sum(1) + 0.5 * (W * np.isin(I, [L.index("neck03")])).sum(1)
    wh = np.clip(wh, 0, 1)[:, None]
    Pw = np.c_[P, np.ones(len(P))] @ M
    return P * (1 - wh) + Pw * wh


def region_colors(rgba, det, cat):
    """Median hair / skin / iris colours from the photo (MediaPipe categories + iris landmarks)."""
    rgb = rgba[..., :3]
    alpha = rgba[..., 3] > 200
    def med(m, fallback):
        px = rgb[m & alpha]
        return np.median(px, 0) if len(px) > 50 else np.array(fallback, np.float32)
    skin = med((cat == 2) | (cat == 3), (205, 160, 140))
    hair = med(cat == 1, skin) if ((cat == 1) & alpha).sum() > 400 else None
    iris = None
    if det.get("face") and len(det["face"]) >= 478:
        f = np.array(det["face"])
        cols = []
        for c_idx, ring in ((468, range(469, 473)), (473, range(474, 478))):
            r = np.linalg.norm(f[list(ring), :2] - f[c_idx, :2], axis=1).mean() * 0.7
            yy, xx = np.mgrid[:rgb.shape[0], :rgb.shape[1]]
            m = (xx - f[c_idx, 0]) ** 2 + (yy - f[c_idx, 1]) ** 2 < r ** 2
            if m.sum() > 3:
                cols.append(rgb[m])
        if cols:
            px = np.concatenate(cols)
            iris = np.median(px[px.sum(1) > np.percentile(px.sum(1), 40)], 0)  # skip the dark pupil
    return skin, hair, iris


def bake(work: Path, params: dict, body_res: dict, size: int = 1024):
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    H, W = rgba.shape[:2]
    model, V, P, s, t, det = posed_mesh(work, params, body_res)
    P = align_head(model, V, P, det)
    F = np.asarray(model.faces)
    uv = model.texture_coordinates.numpy()
    UI = np.asarray(model.face_texture_coordinate_indices)
    labels = list(model.bone_labels)
    Wt, It = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    dom = It[np.arange(len(It)), Wt.argmax(1)]
    vpart = np.array([part_of(labels[b]) for b in dom])

    # z-buffer of the posed mesh in photo space (with the head-aligned projection)
    Vimg = np.stack([P[:, 0], V[:, 1], -P[:, 1]], 1)  # x=img x, y=depth, z=-img y
    _, tid, _ = rasterize(Vimg, F, np.zeros((len(F), 3)), center=(W / 2, 0, -H / 2), scale=1.0, size=W)
    zbuf = np.full((H, W), np.inf, np.float32)
    # depth per pixel from the front-most triangle (centroid depth is enough for a visibility test)
    cz = V[F][:, :, 1].mean(1)
    zbuf[tid >= 0] = cz[tid[tid >= 0]]
    front_part = np.full((H, W), "", object)
    front_part[tid >= 0] = vpart[F[tid[tid >= 0], 0]]

    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    cat = preprocess.person_categories(np.ascontiguousarray(rgba[..., :3]))
    skin, hair, iris = region_colors(rgba, det, cat)
    # Only sample well inside the silhouette: border pixels mix in the removed background.
    inner = cv2.erode((rgba[..., 3] > 200).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
    alpha = inner
    skin_px = (cat == 2) | (cat == 3)
    is_hand = np.array([labels[b].startswith(("wrist", "finger", "metacarpal")) for b in dom])

    back = None  # optional AI back view (fit/backview.py), mirrored horizontally
    if (work / "back_cutout.png").exists():
        back = cv2.cvtColor(cv2.imread(str(work / "back_cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        back = cv2.resize(back, (W, H))
    tex = np.zeros((size, size, 3), np.float32)
    valid = np.zeros((size, size), bool)
    hand_tex = np.zeros((size, size), bool)
    torso_or_leg = np.array([vpart[f[0]] in ("torso", "leg_L", "leg_R") for f in F])
    # Hair colour only on the scalp: pure head-bone vertices above the ears (not the nape / neck).
    head_w = (Wt * (It == labels.index("head"))).sum(1)
    ear_y = chin_y = None
    if det.get("face"):
        f = np.array(det["face"])
        ear_y, chin_y = (f[234, 1] + f[454, 1]) / 2, f[152, 1]
    tri_y = P[F][:, :, 1].mean(1)
    scalp_limit = (ear_y + 0.3 * (chin_y - ear_y)) if ear_y is not None else np.inf
    head_tris = (head_w[F].min(1) > 0.9) & (tri_y < scalp_limit)
    eps = 0.03  # m
    for i in range(len(F)):
        tuv = uv[UI[i]] * [size - 1, -(size - 1)] + [0, size - 1]
        x0, x1 = int(np.floor(tuv[:, 0].min())), int(np.ceil(tuv[:, 0].max()))
        y0, y1 = int(np.floor(tuv[:, 1].min())), int(np.ceil(tuv[:, 1].max()))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        a, b, c = tuv
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        w2 = 1 - w0 - w1
        m = (w0 >= -0.02) & (w1 >= -0.02) & (w2 >= -0.02)
        if not m.any():
            continue
        w = np.stack([w0[m], w1[m], w2[m]], 1)
        pimg = w @ P[F[i]]
        depth = w @ V[F[i], 1]
        px = np.clip(pimg[:, 0].round().astype(int), 0, W - 1)
        py = np.clip(pimg[:, 1].round().astype(int), 0, H - 1)
        tx_, ty_ = xs[m], ys[m]
        facing = n[i, 1] < -0.1  # towards the camera
        grazing = -0.35 < n[i, 1] < 0.35  # nearly edge-on: stretched, unreliable colour
        inside = alpha[py, px]
        visible = inside & (depth <= zbuf[py, px] + eps)
        same_part = front_part[py, px] == vpart[F[i, 0]]
        if back is not None and n[i, 1] > 0.05:  # facing away: use the generated back view
            bx = (W - 1) - px
            ok = back[py, bx, 3] > 127
            col = back[py, bx, :3].astype(np.float32)
        elif head_tris[i] and not facing:
            col = np.tile(hair if hair is not None else skin, (len(px), 1))
            ok = np.ones(len(px), bool)
            # still use the photo where the back-facing scalp is actually visible (e.g. hair on top)
            vis_hair = visible & (n[i, 2] > 0.3)
            col[vis_hair] = rgba[py[vis_hair], px[vis_hair], :3]
        else:
            back_fill = ~facing & inside & same_part
            if torso_or_leg[i]:  # don't carry hands/arms in front of the body onto its back
                back_fill &= ~skin_px[py, px]
            ok = (visible | back_fill) & ~grazing
            if is_hand[F[i, 0]]:  # hands must show skin (e.g. hands on hips over a shirt)
                ok &= skin_px[py, px]
                hand_tex[ty_, tx_] = True
            col = rgba[py, px, :3].astype(np.float32)
        tex[ty_[ok], tx_[ok]] = col[ok]
        valid[ty_[ok], tx_[ok]] = True

    # Hands without a reliable skin sample get the skin colour rather than neighbouring clothes.
    fill_hand = hand_tex & ~valid
    tex[fill_hand] = skin
    valid |= fill_hand
    # Fill the rest in UV space (occluded / outside silhouette), then bleed past island borders.
    tex8 = np.clip(tex, 0, 255).astype(np.uint8)
    hole = (~valid).astype(np.uint8)
    base = tex8.copy()
    base[~valid] = skin.astype(np.uint8)
    filled = cv2.inpaint(base, cv2.dilate(hole, np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA)
    filled[valid] = tex8[valid]
    out = work / "texture.png"
    cv2.imwrite(str(out), cv2.cvtColor(filled, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(work / "texture_valid.png"), (valid * 255).astype(np.uint8))
    meta = {"texture": str(out), "ai_backview": back is not None, "skin": skin.tolist(), "hair": None if hair is None else hair.tolist(),
            "iris": None if iris is None else iris.tolist(), "coverage": float(valid.mean())}
    json.dump(meta, open(work / "texture.json", "w"), indent=1)
    return meta


if __name__ == "__main__":
    import sys, time
    root = Path(__file__).resolve().parents[2] / "build" / "fit"
    for name in sys.argv[1:]:
        t = time.time()
        w = root / name
        meta = bake(w, json.load(open(w / "params.json")), json.load(open(w / "body_params.json")))
        print(name, f"{time.time()-t:.0f}s", {k: (np.round(v).tolist() if isinstance(v, list) else v) for k, v in meta.items() if k != "texture"})


def bake_multiview(work: Path, params: dict, mv: dict, size: int = 1024, face_photo_res: dict | None = None):
    """Texture from the AI turnaround views: each texel takes the view that faces it best.
    face_photo_res (the single-photo body fit): take the face from the ORIGINAL photo instead of the
    AI front (likeness; keeps glasses/accessories that were in the photo)."""
    from .multiview import _rotz
    views = json.load(open(work / "views.json"))
    lcs = params["local_changes"]
    model = anny.Anny(topology="anny-full", local_changes=list(lcs), facial_actions="all").to(dtype=torch.float32)
    L = list(model.bone_labels)
    def posed(arm_rv):
        pose = torch.eye(4).repeat(1, model.bone_count, 1, 1)
        for b, rv in mv["pose_rotvec"].items():
            r = torch.tensor(rv) + torch.tensor(arm_rv.get(b, [0.0, 0.0, 0.0]))
            pose[0, L.index(b), :3, :3] = roma.rotvec_to_rotmat(r)
        with torch.no_grad():
            return model(pose_parameters=pose, phenotype_kwargs=params["phenotype"],
                         local_changes_kwargs=lcs)["vertices"][0].numpy()
    V_views = {name: posed(cam.get("arm_rotvec", {})) for name, cam in mv["multiview"].items()}
    V = V_views["front"]
    F = np.asarray(model.faces)
    uv = model.texture_coordinates.numpy()
    UI = np.asarray(model.face_texture_coordinate_indices)
    Wt, It = model.vertex_bone_weights.numpy(), model.vertex_bone_indices.numpy()
    dom = It[np.arange(len(It)), Wt.argmax(1)]
    is_hand = np.array([L[b].startswith(("wrist", "finger", "metacarpal")) for b in dom])
    vpart_mv = np.array([part_of(L[b]) for b in dom])
    torso_or_leg = np.isin(vpart_mv[F[:, 0]], ("torso", "leg_L", "leg_R"))
    vd = []
    for name, cam in mv["multiview"].items():
        V = V_views[name]
        n_world = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        n_world /= np.linalg.norm(n_world, axis=1, keepdims=True) + 1e-12
        rgba = cv2.cvtColor(cv2.imread(views[name]["path"], cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        H, W = rgba.shape[:2]
        R = _rotz(cam["yaw"]).numpy()
        Vr = V @ R.T
        P = np.stack([cam["scale"] * Vr[:, 0] + cam["tx"], -cam["scale"] * Vr[:, 2] + cam["ty"]], 1)
        if name == "front":
            fk, fface, _ = preprocess.detect(rgba)
            if fface is not None:
                P = align_head(model, V, P, {"face": fface.tolist()})
        Vimg = np.stack([P[:, 0], Vr[:, 1], -P[:, 1]], 1)
        _, tid, _ = rasterize(Vimg, F, np.zeros((len(F), 3)), center=(W / 2, 0, -H / 2), scale=1.0, size=W)
        zbuf = np.full((H, W), np.inf, np.float32)
        cz = Vr[F][:, :, 1].mean(1)
        zbuf[tid >= 0] = cz[tid[tid >= 0]]
        cat = preprocess.person_categories(np.ascontiguousarray(rgba[..., :3]))
        inner = cv2.erode((rgba[..., 3] > 200).astype(np.uint8), np.ones((7, 7), np.uint8)) > 0
        vd.append(dict(name=name, rgba=rgba, P=P, depth=Vr[:, 1], zbuf=zbuf, inner=inner,
                       skin=(cat == 2) | (cat == 3), facing=-(n_world @ R.T)[:, 1], H=H, W=W))

    head_face = np.isin(np.array([L[b] for b in dom])[F[:, 0]], ("head", "eye.L", "eye.R"))
    if face_photo_res is not None:  # original photo as an extra, head-only, preferred view
        model0, V0, P0, _, _, det0 = posed_mesh(work, params, face_photo_res)
        P0 = align_head(model0, V0, P0, det0)
        rgba0 = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        H0, W0 = rgba0.shape[:2]
        Vimg0 = np.stack([P0[:, 0], V0[:, 1], -P0[:, 1]], 1)
        _, tid0, _ = rasterize(Vimg0, F, np.zeros((len(F), 3)), center=(W0 / 2, 0, -H0 / 2), scale=1.0, size=W0)
        zb0 = np.full((H0, W0), np.inf, np.float32)
        zb0[tid0 >= 0] = V0[F][:, :, 1].mean(1)[tid0[tid0 >= 0]]
        n0 = np.cross(V0[F[:, 1]] - V0[F[:, 0]], V0[F[:, 2]] - V0[F[:, 0]])
        n0 /= np.linalg.norm(n0, axis=1, keepdims=True) + 1e-12
        cat0 = preprocess.person_categories(np.ascontiguousarray(rgba0[..., :3]))
        vd.append(dict(name="photo", rgba=rgba0, P=P0, depth=V0[:, 1], zbuf=zb0,
                       inner=cv2.erode((rgba0[..., 3] > 200).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0,
                       skin=(cat0 == 2) | (cat0 == 3), facing=-n0[:, 1], H=H0, W=W0, head_only=True))
    tex = np.zeros((size, size, 3), np.float32)
    best = np.full((size, size), -1.0, np.float32)
    hand_tex = np.zeros((size, size), bool)
    for i in range(len(F)):
        tuv = uv[UI[i]] * [size - 1, -(size - 1)] + [0, size - 1]
        x0, x1 = int(np.floor(tuv[:, 0].min())), int(np.ceil(tuv[:, 0].max()))
        y0, y1 = int(np.floor(tuv[:, 1].min())), int(np.ceil(tuv[:, 1].max()))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        a, b, c = tuv
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        m = (w0 >= -0.02) & (w1 >= -0.02) & (1 - w0 - w1 >= -0.02)
        if not m.any():
            continue
        w = np.stack([w0[m], w1[m], 1 - w0[m] - w1[m]], 1)
        tx_, ty_ = xs[m], ys[m]
        hand = is_hand[F[i, 0]]
        if hand:
            hand_tex[ty_, tx_] = True
        for v in vd:
            score = v["facing"][i]
            if v.get("head_only"):
                if not head_face[i] or score < 0.35:
                    continue
                score += 1.0  # the real photo wins wherever it sees the face
            if score < 0.25:
                continue
            p = w @ v["P"][F[i]]
            px = np.clip(p[:, 0].round().astype(int), 0, v["W"] - 1)
            py = np.clip(p[:, 1].round().astype(int), 0, v["H"] - 1)
            ok = v["inner"][py, px] & (w @ v["depth"][F[i]] <= v["zbuf"][py, px] + 0.03)
            if hand:
                ok &= v["skin"][py, px]
            elif torso_or_leg[i]:  # a hand hanging in front of the hip/thigh in some view
                ok &= ~v["skin"][py, px]
            ok &= score > best[ty_, tx_]
            tex[ty_[ok], tx_[ok]] = v["rgba"][py[ok], px[ok], :3]
            best[ty_[ok], tx_[ok]] = score
    valid = best > 0
    skin = np.median(np.concatenate([v["rgba"][..., :3][v["skin"] & v["inner"]] for v in vd]), 0) \
        if any((v["skin"] & v["inner"]).any() for v in vd) else np.array([205, 160, 140], np.float32)
    fill_hand = hand_tex & ~valid
    tex[fill_hand] = skin
    valid |= fill_hand
    tex8 = np.clip(tex, 0, 255).astype(np.uint8)
    base = tex8.copy()
    base[~valid] = skin.astype(np.uint8)
    filled = cv2.inpaint(base, cv2.dilate((~valid).astype(np.uint8), np.ones((3, 3), np.uint8)), 7, cv2.INPAINT_TELEA)
    filled[valid] = tex8[valid]
    out = work / "texture.png"
    cv2.imwrite(str(out), cv2.cvtColor(filled, cv2.COLOR_RGB2BGR))
    cv2.imwrite(str(work / "texture_valid.png"), (valid * 255).astype(np.uint8))
    # iris colour still from the original photo (the AI views are small)
    rgba0 = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    det0 = json.load(open(work / "detections.json"))
    _, hair, iris = region_colors(rgba0, det0, preprocess.person_categories(np.ascontiguousarray(rgba0[..., :3])))
    meta = {"texture": str(out), "ai_backview": False, "ai_turnaround": True, "skin": skin.tolist(),
            "face_from": "photo" if face_photo_res is not None else "ai",
            "hair": None if hair is None else hair.tolist(), "iris": None if iris is None else iris.tolist(),
            "coverage": float(valid.mean())}
    json.dump(meta, open(work / "texture.json", "w"), indent=1)
    return meta
