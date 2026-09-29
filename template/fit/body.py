"""Fit Anny body shape (+ a nuisance pose and an orthographic camera) to a prepared photo.

Signals: MediaPipe 2D keypoints ↔ Anny COCO keypoint regressor, and the foreground silhouette
(vertices must fall inside it; its contour should be covered by the body). The pose only serves
to explain the photo; the exported avatar is always re-posed to a T-pose.
"""
from __future__ import annotations

import json
from pathlib import Path

import anny
import cv2
import numpy as np
import roma
import torch

PHENO = ["gender", "age", "muscle", "weight", "height", "proportions"]
BODY_LC = [
    "measure-upperarm-length-incr", "measure-lowerarm-length-incr", "measure-upperleg-height-incr",
    "measure-lowerleg-height-incr", "measure-shoulder-dist-incr", "measure-napetowaist-dist-incr",
    "measure-waisttohip-dist-incr", "measure-neck-height-incr", "measure-waist-circ-incr",
    "measure-hips-circ-incr", "measure-bust-circ-incr", "measure-thigh-circ-incr",
    "measure-upperarm-circ-incr", "measure-calf-circ-incr",
    "head-scale-vert-incr", "head-scale-horiz-incr", "head-scale-depth-incr",
    "torso-scale-horiz-incr", "hip-scale-horiz-incr",
    "l-hand-scale-incr", "r-hand-scale-incr", "l-foot-scale-incr", "r-foot-scale-incr",
]
POSE_BONES = ["root", "spine03", "spine01", "neck01", "head", "clavicle.L", "clavicle.R",
              "upperarm01.L", "upperarm01.R", "lowerarm01.L", "lowerarm01.R",
              "upperleg01.L", "upperleg01.R", "lowerleg01.L", "lowerleg01.R", "foot.L", "foot.R"]
POSE_PRIOR = torch.tensor([0.0 if b == "root" else 2e-3 if b in ("spine03", "spine01", "neck01", "head", "clavicle.L", "clavicle.R", "foot.L", "foot.R") else 2e-4 for b in POSE_BONES])
# Stylized (cartoon) mode: these shape targets may be extrapolated beyond the human range.
STYLIZED_RANGE = {"head-scale-vert-incr": 3.0, "head-scale-horiz-incr": 3.0, "head-scale-depth-incr": 3.0,
                  "measure-upperleg-height-incr": 2.0, "measure-lowerleg-height-incr": 2.0,
                  "measure-upperarm-length-incr": 2.0, "measure-lowerarm-length-incr": 2.0,
                  "measure-neck-height-incr": 2.0, "torso-scale-horiz-incr": 2.0, "hip-scale-horiz-incr": 2.0,
                  "measure-waist-circ-incr": 2.0, "l-hand-scale-incr": 2.5, "r-hand-scale-incr": 2.5,
                  "l-foot-scale-incr": 2.5, "r-foot-scale-incr": 2.5}
# Stylized mode may also scale whole bones (head, hands, feet, legs) — cartoons need ratios that no
# human shape target reaches. Uniform scale about the bone head; baked into the rest pose on export.
SCALE_BONES = ["head", "wrist.L", "wrist.R", "foot.L", "foot.R",
               "upperleg01.L", "upperleg01.R", "lowerleg01.L", "lowerleg01.R", "spine03"]
HEAD_KPS = {"nose", "left_eye", "right_eye", "left_ear", "right_ear"}
KP_WEIGHT = {"nose": 0.5, "left_eye": 0.3, "right_eye": 0.3, "left_ear": 0.3, "right_ear": 0.3}

torch.set_num_threads(max(1, torch.get_num_threads()))


def build_model(local_changes=BODY_LC):
    return anny.Anny(local_changes=list(local_changes), phenotypes="default").to(dtype=torch.float32)


class Fitter(torch.nn.Module):
    def __init__(self, model, kp_labels, stylized=False):
        super().__init__()
        self.lc_range = torch.tensor([STYLIZED_RANGE.get(l, 1.0) if stylized else 1.0
                                      for l in model.local_change_labels])
        self.model = model
        self.kpr = anny.KeypointsRegressor.coco(model, labels=kp_labels)
        B = model.bone_count
        self.bone_idx = [list(model.bone_labels).index(b) for b in POSE_BONES]
        self.B = B
        self.rv = torch.nn.Parameter(torch.zeros(len(POSE_BONES), 3))
        self.pheno_raw = torch.nn.Parameter(torch.zeros(len(model.phenotype_labels)))
        self.lc_raw = torch.nn.Parameter(torch.zeros(len(model.local_change_labels)))
        self.cam = torch.nn.Parameter(torch.zeros(3))  # log-scale, tx, ty
        self.stylized = stylized
        self.scale_idx = [list(model.bone_labels).index(b) for b in SCALE_BONES]
        self.log_scale = torch.nn.Parameter(torch.zeros(len(SCALE_BONES)))

    def pheno(self):
        return torch.sigmoid(self.pheno_raw)

    def lc(self):
        return torch.tanh(self.lc_raw / self.lc_range) * self.lc_range

    def forward(self, s0, t0):
        pose = torch.eye(4).repeat(1, self.B, 1, 1)
        R = roma.rotvec_to_rotmat(self.rv)
        pose = pose.clone()
        pose[0, self.bone_idx, :3, :3] = R
        if self.stylized:
            sc = torch.exp(self.log_scale.clamp(-0.9, 1.2))
            pose[0, self.scale_idx, :3, :3] = pose[0, self.scale_idx, :3, :3] * sc[:, None, None]
        out = self.model(pose_parameters=pose, phenotype_kwargs=self.pheno()[None],
                         local_changes_kwargs=self.lc()[None])
        V = out["vertices"][0]
        kp = self.kpr(out)[0]
        s = s0 * torch.exp(self.cam[0])
        tx, ty = t0[0] + self.cam[1] * s0, t0[1] + self.cam[2] * s0

        def proj(X):
            return torch.stack([s * X[:, 0] + tx, -s * X[:, 2] + ty], 1)
        return proj(V), proj(kp), V, s


_TPOSE_RV = None


def tpose_rotvecs(model) -> torch.Tensor:
    """Local-ref rotation vectors (per POSE_BONES) that put Anny's arms straight and horizontal."""
    global _TPOSE_RV
    torch.set_grad_enabled(True)
    if _TPOSE_RV is not None:
        return _TPOSE_RV
    L = list(model.bone_labels)
    idx = [L.index(b) for b in POSE_BONES]
    arm = [POSE_BONES.index(b) for b in ("upperarm01.L", "upperarm01.R", "lowerarm01.L", "lowerarm01.R")]
    rv = torch.zeros(len(POSE_BONES), 3)
    rv[arm[0], 1], rv[arm[1], 1] = -0.84, 0.84
    rv = rv.requires_grad_(True)
    opt = torch.optim.Adam([rv], lr=0.02)
    j = {n: L.index(n) for n in ("upperarm01.L", "lowerarm01.L", "wrist.L", "upperarm01.R", "lowerarm01.R", "wrist.R")}
    for _ in range(300):
        opt.zero_grad()
        pose = torch.eye(4).repeat(1, model.bone_count, 1, 1).clone()
        mask = torch.zeros(len(POSE_BONES), 1)
        mask[arm] = 1
        pose[0, idx, :3, :3] = roma.rotvec_to_rotmat(rv * mask)
        P = model(pose_parameters=pose)["bone_poses"][0][:, :3, 3]
        loss = 0
        for s, sign in (("L", 1), ("R", -1)):
            sh = P[j[f"upperarm01.{s}"]]
            for n in (f"lowerarm01.{s}", f"wrist.{s}"):
                d = P[j[n]] - sh
                loss = loss + d[1] ** 2 + d[2] ** 2 - 0.01 * sign * d[0]
        loss.backward()
        opt.step()
    _TPOSE_RV = (rv.detach() * mask).clone()
    return _TPOSE_RV


def is_tpose_silhouette(mask: np.ndarray) -> bool:
    """Arms spread horizontally: some row in the upper half is > 2x as wide as the hip rows."""
    ys, xs = np.where(mask)
    y0, h = ys.min(), ys.max() - ys.min()
    def width(y):
        row = np.where(mask[int(y)])[0]
        return row.max() - row.min() if len(row) else 0
    upper = max(width(y0 + f * h) for f in np.linspace(0.15, 0.55, 20))
    hips = np.median([width(y0 + f * h) for f in np.linspace(0.55, 0.65, 5)])
    return upper > 2.0 * hips


def head_ratio(prep_dir: Path) -> float | None:
    """Face width / person height. Real people ≈ 0.05–0.10; chibi/cartoon characters ≫ 0.15."""
    det = json.load(open(prep_dir / "detections.json"))
    if not det.get("face"):
        return None
    mask = cv2.imread(str(prep_dir / "cutout.png"), cv2.IMREAD_UNCHANGED)[..., 3] > 127
    ys = np.where(mask)[0]
    return float(np.ptp(np.array(det["face"])[:, 0]) / (ys.max() - ys.min()))


def choose_and_fit(prep_dir: Path, gender_init=0.5, verbose=False):
    """Realistic fit by default; stylized (bone scales, extrapolated shapes) only for cartoon
    proportions. Loose clothing alone must not trigger it, so the cue is head size, not fit error."""
    hr = head_ratio(prep_dir)
    stylized = hr is not None and hr > 0.15
    res = fit(prep_dir, verbose=verbose, gender_init=gender_init, stylized=stylized)
    res[0]["head_ratio"] = hr
    return res


def gmof(r2, sigma2):
    return sigma2 * r2 / (sigma2 + r2)


def fit(prep_dir: Path, iters=(500, 300), verbose=True, gender_init=0.5, stylized=False):
    det = json.load(open(prep_dir / "detections.json"))
    rgba = cv2.imread(str(prep_dir / "cutout.png"), cv2.IMREAD_UNCHANGED)
    mask = rgba[..., 3] > 127
    H, W = mask.shape
    ys, xs = np.where(mask)
    person_h = float(ys.max() - ys.min())

    kps = {k: v for k, v in det["keypoints"].items()}
    labels = list(kps)
    obs = torch.tensor([[kps[k][0], kps[k][1]] for k in labels], dtype=torch.float32)
    vis = torch.tensor([kps[k][2] * KP_WEIGHT.get(k, 1.0) * (1.0 if not stylized else 0.02)
                        for k in labels], dtype=torch.float32)

    dt_out = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5).astype(np.float32)
    dt_t = torch.from_numpy(dt_out)[None, None]
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contour = np.concatenate([c[:, 0] for c in cnts]).astype(np.float32)
    contour = torch.from_numpy(contour[np.linspace(0, len(contour) - 1, 800).astype(int)])

    model = build_model()
    f = Fitter(model, labels, stylized)
    fixed_pose = stylized and is_tpose_silhouette(mask)
    if fixed_pose:  # cartoon in T-pose: freeze a canonical T-pose so shape must explain the silhouette
        rv_t = tpose_rotvecs(model)
        with torch.no_grad():
            f.rv.copy_(rv_t)
    with torch.no_grad():
        f.pheno_raw[list(model.phenotype_labels).index('gender')] = float(np.log(gender_init / (1 - gender_init)))
    s0 = person_h / 1.70
    t0 = torch.tensor([(xs.min() + xs.max()) / 2, ys.min() + 0.93 * person_h * 0.0 + 0.0])
    # Anny's origin is the pelvis (~0.84 m above the soles); put it at 45% of the person height.
    t0 = torch.tensor([float((xs.min() + xs.max()) / 2), float(ys.min() + 0.47 * person_h)])

    def sample_dt(p):
        g = torch.stack([p[:, 0] / (W - 1) * 2 - 1, p[:, 1] / (H - 1) * 2 - 1], 1)[None, None]
        return torch.nn.functional.grid_sample(dt_t, g, align_corners=True)[0, 0, 0]

    sub = torch.arange(0, model.template_vertices.shape[0], 1 if stylized else 4)
    w_in, w_cov = (40, 30) if stylized else (20, 5)
    sig2 = (0.04 * person_h) ** 2
    history = []
    for stage, n in enumerate(iters):
        params = [f.cam, f.rv] if stage == 0 else [f.cam, f.rv, f.pheno_raw, f.lc_raw]
        if stylized:  # silhouette-driven from the start
            params = [f.cam, f.pheno_raw, f.lc_raw, f.log_scale] + ([] if fixed_pose else [f.rv])
        opt = torch.optim.Adam(params, lr=0.05 if stage == 0 else 0.02)
        for it in range(n):
            opt.zero_grad()
            pv, pk, V, s = f(s0, t0)
            r2 = ((pk - obs) ** 2).sum(1)
            l_kp = (vis * gmof(r2, sig2)).sum() / (vis.sum() * person_h ** 2)
            loss = 10 * l_kp
            l_in = l_cov = torch.tensor(0.0)
            if stage > 0 or stylized:
                l_in = (sample_dt(pv[sub]) / person_h).pow(2).mean()
                d = torch.cdist(contour, pv[sub]).min(1).values / person_h
                # stylized: wide robust kernel annealed coarse→fine so far-away contour parts still pull
                sig = 0.03 if not stylized else max(0.03, 0.25 * (1 - it / n))
                l_cov = gmof(d ** 2, sig ** 2).mean()
                loss = loss + w_in * l_in + w_cov * l_cov
                loss = loss + 1e-3 * ((f.pheno() - 0.5) ** 2).sum() + 5e-4 * (f.lc() ** 2).sum()
                loss = loss + 2e-3 * (f.log_scale ** 2).sum()
                # left/right symmetry of bone scales
                ls = f.log_scale
                loss = loss + 0.05 * ((ls[1] - ls[2]) ** 2 + (ls[3] - ls[4]) ** 2 + (ls[5] - ls[6]) ** 2 + (ls[7] - ls[8]) ** 2)
            loss = loss + (POSE_PRIOR * (f.rv ** 2).sum(1)).sum()
            loss.backward()
            opt.step()
            if verbose and (it % 50 == 0 or it == n - 1):
                history.append((stage, it, l_kp.item(), l_in.item(), l_cov.item()))
                print(f"  stage{stage} it{it:3d} kp={l_kp.item():.5f} in={l_in.item():.5f} cov={l_cov.item():.5f}")

    with torch.no_grad():
        pv, pk, V, s = f(s0, t0)
    final_loss = float(loss.detach())
    result = {
        "loss": final_loss, "stylized": stylized,
        "kp_error": float(l_kp.detach()), "inside": float(l_in.detach()), "coverage": float(l_cov.detach()),
        "phenotype": {k: float(v) for k, v in zip(model.phenotype_labels, f.pheno())},
        "local_changes": {k: float(v) for k, v in zip(model.local_change_labels, f.lc())},
        "pose_rotvec": {b: f.rv[i].tolist() for i, b in enumerate(POSE_BONES)},
        "bone_scale": {b: float(torch.exp(f.log_scale[i].clamp(-0.9, 1.2))) for i, b in enumerate(SCALE_BONES)} if stylized else {},
        "camera": {"scale": float(s), "t0": t0.tolist(), "cam": f.cam.tolist(), "s0": s0},
    }
    return result, pv.numpy(), pk.numpy(), obs.numpy(), np.asarray(model.faces), V.numpy()


def render_overlay(rgba, pv, faces, V, pk=None, obs=None):
    a = rgba[..., 3:4].astype(np.float32) / 255
    img = (rgba[..., :3].astype(np.float32) * a + 235 * (1 - a)).astype(np.uint8).copy()
    layer = img.copy()
    tri = pv[faces]
    n = np.cross(V[faces][:, 1] - V[faces][:, 0], V[faces][:, 2] - V[faces][:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    front = -n[:, 1]  # facing the camera (-Y)
    depth = V[faces][:, :, 1].mean(1)
    for i in np.argsort(-depth):
        if front[i] <= 0:
            continue
        c = int(80 + 170 * front[i])
        cv2.fillConvexPoly(layer, tri[i].astype(np.int32), (c, int(c * 0.75), int(c * 0.6)))
    out = cv2.addWeighted(img, 0.45, layer, 0.55, 0)
    if pk is not None:
        for (x, y), (ox, oy) in zip(pk, obs):
            cv2.line(out, (int(x), int(y)), (int(ox), int(oy)), (255, 255, 0), 2)
            cv2.circle(out, (int(ox), int(oy)), 5, (255, 40, 40), -1)
            cv2.circle(out, (int(x), int(y)), 4, (40, 200, 255), -1)
    return out


if __name__ == "__main__":
    import sys, time
    root = Path(__file__).resolve().parents[2] / "build" / "fit"
    for name in sys.argv[1:]:
        t = time.time()
        d = root / name
        res, pv, pk, obs, faces, V = choose_and_fit(d)
        res["gender_losses"] = [res["loss"]]
        json.dump(res, open(d / "body_params.json", "w"), indent=1)
        rgba = cv2.cvtColor(cv2.imread(str(d / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        cv2.imwrite(str(d / "body_fit.png"), cv2.cvtColor(render_overlay(rgba, pv, faces, V, pk, obs), cv2.COLOR_RGB2BGR))
        ph = {k: round(v, 2) for k, v in res["phenotype"].items()}
        top = sorted(res["local_changes"].items(), key=lambda kv: -abs(kv[1]))[:5]
        print(f"{name}: {time.time()-t:.0f}s losses={[round(x, 5) for x in res['gender_losses']]} pheno={ph} top_lc={[(k, round(v, 2)) for k, v in top]}")
