"""Photo → background-removed, centered square RGBA + MediaPipe pose / face detections.

Segmentation (no heavy downloads): real alpha if present; otherwise MediaPipe pose segmentation
(or a border-colour model when no person is detected, e.g. cartoons) seeding OpenCV GrabCut.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

MODELS = Path(__file__).resolve().parents[2] / "build" / "models"
SIZE = 1024
MARGIN = 0.06
# The Metal GPU delegate aborts in headless Python on macOS ("Service is unavailable"); use CPU.
CPU = mpt.BaseOptions.Delegate.CPU

# MediaPipe pose index → Anny COCO keypoint label (both "left" = subject's left).
MP_TO_COCO = {
    0: "nose", 2: "left_eye", 5: "right_eye", 7: "left_ear", 8: "right_ear",
    11: "left_shoulder", 12: "right_shoulder", 13: "left_elbow", 14: "right_elbow",
    15: "left_wrist", 16: "right_wrist", 23: "left_hip", 24: "right_hip",
    25: "left_knee", 26: "right_knee", 27: "left_ankle", 28: "right_ankle",
    29: "left_heel", 30: "right_heel", 31: "left_big_toe", 32: "right_big_toe",
}


@dataclass
class Prepared:
    rgba: np.ndarray                     # (SIZE, SIZE, 4) uint8, centered, background removed
    mask: np.ndarray                     # (SIZE, SIZE) float32 in [0,1]
    seg_method: str
    keypoints: dict = field(default_factory=dict)   # coco label → (x, y, visibility) in px
    face: np.ndarray | None = None       # (478, 3) px x,y and MediaPipe z (px-scaled)
    blendshapes: dict = field(default_factory=dict)

    def save(self, out: Path):
        out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / "cutout.png"), cv2.cvtColor(self.rgba, cv2.COLOR_RGBA2BGRA))
        json.dump({
            "seg_method": self.seg_method, "keypoints": self.keypoints,
            "face": None if self.face is None else self.face.round(2).tolist(),
            "blendshapes": self.blendshapes,
        }, open(out / "detections.json", "w"))


def _pose_landmarker(seg=True):
    return vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELS / "pose_landmarker_heavy.task"), delegate=CPU),
        running_mode=vision.RunningMode.IMAGE, output_segmentation_masks=seg, num_poses=1,
        min_pose_detection_confidence=0.3, min_pose_presence_confidence=0.3))


def _face_landmarker():
    return vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELS / "face_landmarker.task"), delegate=CPU),
        running_mode=vision.RunningMode.IMAGE, num_faces=1, output_face_blendshapes=True,
        min_face_detection_confidence=0.3))


def _segmenter():
    return vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELS / "selfie_multiclass_256x256.tflite"), delegate=CPU),
        running_mode=vision.RunningMode.IMAGE, output_category_mask=True, output_confidence_masks=False))


def person_categories(rgb: np.ndarray) -> np.ndarray:
    """uint8 per-pixel class: 0 background, 1 hair, 2 body skin, 3 face skin, 4 clothes, 5 other.
    (Only the uint8 category mask is used: float masks crash in MediaPipe 0.10.x on macOS.)"""
    with _segmenter() as sg:
        r = sg.segment(_mp_image(rgb))
    cat = np.squeeze(r.category_mask.numpy_view()).copy()
    return cv2.resize(cat, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_NEAREST)


def _mp_image(rgb: np.ndarray):
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))


def _largest_component(mask: np.ndarray) -> np.ndarray:
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask.astype(bool)
    keep = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    m = lab == keep
    # fill holes
    inv = (~m).astype(np.uint8)
    n2, lab2, stats2, _ = cv2.connectedComponentsWithStats(inv, 4)
    h, w = m.shape
    for i in range(1, n2):
        x, y, ww, hh, _ = stats2[i]
        if x > 0 and y > 0 and x + ww < w and y + hh < h:
            m |= lab2 == i
    return m


SKELETON = [(11, 12), (11, 23), (12, 24), (23, 24), (11, 13), (13, 15), (12, 14), (14, 16),
            (23, 25), (25, 27), (24, 26), (26, 28), (27, 31), (28, 32), (0, 11), (0, 12)]


def segment(rgb: np.ndarray, alpha: np.ndarray | None) -> tuple[np.ndarray, str]:
    """Foreground mask. Seeds GrabCut from pose landmarks (MediaPipe's float masks are unreadable
    in 0.10.x on macOS) and from a border-colour background model."""
    if alpha is not None and (alpha < 128).mean() > 0.05:
        return (alpha > 127), "alpha"
    h, w = rgb.shape[:2]
    gc = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    border = np.concatenate([rgb[:6].reshape(-1, 3), rgb[-6:].reshape(-1, 3),
                             rgb[:, :6].reshape(-1, 3), rgb[:, -6:].reshape(-1, 3)]).astype(np.float32)
    # distance to the closest of a few border colours (handles two-tone checkerboards)
    k = min(4, len(border))
    _, _, centers = cv2.kmeans(border, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1), 3, cv2.KMEANS_PP_CENTERS)
    diff = np.min(np.linalg.norm(rgb.astype(np.float32)[..., None, :] - centers[None, None], axis=3), axis=2)
    gc[diff > 35] = cv2.GC_PR_FGD
    person = person_categories(rgb) > 0
    gc[person] = cv2.GC_PR_FGD
    gc[cv2.erode(person.astype(np.uint8), np.ones((11, 11), np.uint8)) > 0] = cv2.GC_FGD

    with _pose_landmarker(seg=False) as lm:
        res = lm.detect(_mp_image(rgb))
    if res.pose_landmarks:
        method = "grabcut+seg+pose"
        pts = np.array([(l.x * w, l.y * h) for l in res.pose_landmarks[0]])
        seed = np.zeros((h, w), np.uint8)
        thick = max(3, int(np.linalg.norm(pts[11] - pts[12]) * 0.12))
        for a, b in SKELETON:
            cv2.line(seed, tuple(map(int, pts[a])), tuple(map(int, pts[b])), 1, thick)
        cv2.fillPoly(seed, [pts[[11, 12, 24, 23]].astype(np.int32)], 1)
        gc[(seed > 0) & (diff > 12)] = cv2.GC_FGD
    else:
        # No person detected (e.g. cartoons): trust strong colour difference from the border.
        method = "grabcut+seg+border"
        core = cv2.erode((diff > 60).astype(np.uint8), np.ones((15, 15), np.uint8))
        gc[core > 0] = cv2.GC_FGD
    b = max(4, min(h, w) // 100)
    gc[:b], gc[-b:], gc[:, :b], gc[:, -b:] = cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD, cv2.GC_BGD
    bgd, fgd = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), gc, None, bgd, fgd, 6, cv2.GC_INIT_WITH_MASK)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    return _largest_component(m), method


def center(rgb: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    side = int(max(y1 - y0, x1 - x0) * (1 + 2 * MARGIN))
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
    M = np.float32([[1, 0, side / 2 - cx], [0, 1, side / 2 - cy]])
    rgba = np.dstack([rgb, (mask * 255).astype(np.uint8)])
    out = cv2.warpAffine(rgba, M, (side, side), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    out = cv2.resize(out, (SIZE, SIZE), interpolation=cv2.INTER_AREA)
    # feather edges a little
    a = cv2.GaussianBlur(out[..., 3].astype(np.float32), (3, 3), 0)
    out[..., 3] = a.astype(np.uint8)
    return out, a / 255.0


def detect(rgba: np.ndarray) -> tuple[dict, np.ndarray | None, dict]:
    a = rgba[..., 3:4].astype(np.float32) / 255
    rgb = (rgba[..., :3] * a + 200 * (1 - a)).astype(np.uint8)  # neutral grey background
    kps: dict = {}
    with _pose_landmarker(seg=False) as lm:
        res = lm.detect(_mp_image(rgb))
    if res.pose_landmarks:
        for i, l in enumerate(res.pose_landmarks[0]):
            if i in MP_TO_COCO:
                kps[MP_TO_COCO[i]] = (l.x * SIZE, l.y * SIZE, float(l.visibility or 0))
    face, shapes = None, {}
    # Face: run on an upscaled head crop for accuracy, fall back to the full image.
    crops = []
    if "nose" in kps:
        ears = [kps[k] for k in ("left_ear", "right_ear", "left_eye", "right_eye", "nose") if k in kps]
        xs, ys = [p[0] for p in ears], [p[1] for p in ears]
        half = max(60.0, (max(xs) - min(xs)) * 1.6)
        cx, cy = np.mean(xs), np.mean(ys)
        crops.append((cx - half, cy - half, 2 * half))
    crops.append((0.0, 0.0, float(SIZE)))
    with _face_landmarker() as fl:
        for x0, y0, side in crops:
            M = np.float32([[512 / side, 0, -x0 * 512 / side], [0, 512 / side, -y0 * 512 / side]])
            crop = cv2.warpAffine(rgb, M, (512, 512), flags=cv2.INTER_CUBIC, borderValue=(200, 200, 200))
            r = fl.detect(_mp_image(crop))
            if r.face_landmarks:
                pts = np.array([(p.x * 512, p.y * 512, p.z * 512) for p in r.face_landmarks[0]], np.float32)
                s = side / 512
                face = np.stack([pts[:, 0] * s + x0, pts[:, 1] * s + y0, pts[:, 2] * s], 1)
                shapes = {c.category_name: float(c.score) for c in r.face_blendshapes[0] if c.category_name != "_neutral"}
                break
    return kps, face, shapes


def prepare(path: str | Path) -> Prepared:
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    alpha = img[..., 3] if img.shape[2] == 4 else None
    rgb = cv2.cvtColor(img[..., :3], cv2.COLOR_BGR2RGB)
    if alpha is not None:  # un-premultiply against white for fully transparent pixels
        rgb = np.where(alpha[..., None] == 0, 255, rgb).astype(np.uint8)
    mask, method = segment(rgb, alpha)
    rgba, soft = center(rgb, mask)
    kps, face, shapes = detect(rgba)
    return Prepared(rgba, soft, method, kps, face, shapes)


def overlay(p: Prepared) -> np.ndarray:
    a = p.rgba[..., 3:4].astype(np.float32) / 255
    vis = (p.rgba[..., :3] * a + np.array([235, 235, 240]) * (1 - a)).astype(np.uint8).copy()
    for name, (x, y, v) in p.keypoints.items():
        cv2.circle(vis, (int(x), int(y)), 7, (255, 60, 60) if v > 0.5 else (255, 180, 0), -1)
    if p.face is not None:
        for x, y, _ in p.face:
            cv2.circle(vis, (int(x), int(y)), 1, (0, 160, 255), -1)
    return vis


if __name__ == "__main__":
    import sys
    root = Path(__file__).resolve().parents[2]
    for f in sys.argv[1:]:
        p = prepare(f)
        out = root / "build" / "fit" / Path(f).stem
        p.save(out)
        cv2.imwrite(str(out / "detections.png"), cv2.cvtColor(overlay(p), cv2.COLOR_RGB2BGR))
        print(f"{Path(f).name:45s} seg={p.seg_method:15s} keypoints={len(p.keypoints):2d} "
              f"face={'yes' if p.face is not None else 'NO '} blendshapes={len(p.blendshapes)}")
