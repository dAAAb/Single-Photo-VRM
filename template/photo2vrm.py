"""Any human-shaped photo → VRM (0.x + 1.0) with Perfect Sync.

    .venv/bin/python photo2vrm.py photo.png [--out build/out/name] [--gender female|male]

Steps: background removal + centering → MediaPipe keypoints / face → Anny body fit
(realistic, or stylized with bone scales when a human body can't explain the photo) → face fit →
T-pose export → Blender VRM build. Nothing here is specific to particular test images.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import cv2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
GENDER = {"female": 0.0, "male": 1.0}


def log(msg):
    print(f"[photo2vrm] {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", help="output prefix (default build/out/<image stem>)")
    ap.add_argument("--gender", choices=list(GENDER), help="optional hint; a single silhouette cannot tell reliably")
    ap.add_argument("--blender", default=BLENDER)
    args = ap.parse_args()

    from fit import body, preprocess
    t0 = time.time()
    img = Path(args.image)
    work = ROOT / "build" / "fit" / img.stem
    out = Path(args.out) if args.out else ROOT / "build" / "out" / img.stem
    out.parent.mkdir(parents=True, exist_ok=True)

    log("1/5 background removal, centering, keypoints")
    prep = preprocess.prepare(img)
    prep.save(work)
    cv2.imwrite(str(work / "detections.png"), cv2.cvtColor(preprocess.overlay(prep), cv2.COLOR_RGB2BGR))
    log(f"    segmentation={prep.seg_method} keypoints={len(prep.keypoints)} face={'yes' if prep.face is not None else 'no'}")

    log("2/5 body fit")
    g0 = GENDER.get(args.gender, 0.5)
    res, pv, pk, obs, faces, V = body.choose_and_fit(work, gender_init=min(max(g0, 0.02), 0.98))
    if args.gender:
        res["phenotype"]["gender"] = g0
    mode = "stylized" if res["stylized"] else "realistic"
    hr = res.get("head_ratio")
    log(f"    mode={mode} head/height={'n/a' if hr is None else f'{hr:.2f}'} kp_err={res['kp_error']:.5f} coverage={res['coverage']:.5f}")
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    cv2.imwrite(str(work / "body_fit.png"), cv2.cvtColor(body.render_overlay(rgba, pv, faces, V, pk, obs), cv2.COLOR_RGB2BGR))

    params = {"phenotype": res["phenotype"], "local_changes": res["local_changes"],
              "bone_scale": res.get("bone_scale", {})}
    from fit import face
    if prep.face is not None and not res["stylized"]:
        log("3/5 face fit (478 landmarks → Anny face shape)")
        params["local_changes"].update(face.fit(work, res))
    else:
        log("3/5 face fit skipped (" + ("stylized/cartoon body" if prep.face is not None else "no face detected") + ")")
    json.dump(params, open(work / "params.json", "w"), indent=1)

    log("4/5 T-pose export")
    npz = work / "anny_tpose.npz"
    subprocess.run([sys.executable, str(HERE / "export_anny.py"), "--params", str(work / "params.json"),
                    "--out", str(npz)], cwd=HERE, check=True, stdout=subprocess.DEVNULL)

    log("5/5 VRM build (Blender)")
    env = {"BLENDER_USER_RESOURCES": str(ROOT / "build" / "blender_user"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([args.blender, "-b", "--python", str(HERE / "build_vrm.py"), "--", str(npz), str(out)],
                       env=env, capture_output=True, text=True)
    if "EXPORT" not in r.stdout or r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("VRM build failed")
    log(f"done in {time.time() - t0:.0f}s → {out.name}.vrm0.vrm / {out.name}.vrm1.vrm")


if __name__ == "__main__":
    main()
