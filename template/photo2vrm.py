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
    ap.add_argument("--hair", default="auto",
                    help="auto (from the photo), none, or a MakeHuman style: short01-04 bob01 bob02 long01 ponytail01 braid01 afro01")
    ap.add_argument("--shoes", default="auto", help="auto (from the photo), none (barefoot) or shoes01–shoes06")
    ap.add_argument("--glasses", default="off", help="off, round or square (frame only)")
    ap.add_argument("--glasses-color", default="20,20,22", help="frame colour R,G,B")
    ap.add_argument("--ai-turnaround", action="store_true",
                    help="OPTIONAL: FLUX.2-klein-4B front/side/back T-pose sheet → 3-view body fit + texture (first use downloads ~15 GB)")
    ap.add_argument("--reuse-ai", action="store_true",
                    help="reuse an existing AI turnaround sheet for this image instead of generating a new one")
    ap.add_argument("--ai-backview", action="store_true",
                    help="OPTIONAL: generate the back with FLUX.2-klein-4B via mflux (first use downloads ~15 GB)")
    args = ap.parse_args()

    from fit import body, preprocess
    t0 = time.time()
    img = Path(args.image)
    work = ROOT / "build" / "fit" / img.stem
    out = Path(args.out) if args.out else ROOT / "build" / "out" / img.stem
    out.parent.mkdir(parents=True, exist_ok=True)

    log("1/6 background removal, centering, keypoints")
    prep = preprocess.prepare(img)
    prep.save(work)
    cv2.imwrite(str(work / "detections.png"), cv2.cvtColor(preprocess.overlay(prep), cv2.COLOR_RGB2BGR))
    log(f"    segmentation={prep.seg_method} keypoints={len(prep.keypoints)} face={'yes' if prep.face is not None else 'no'}")

    log("2/6 body fit")
    g0 = GENDER.get(args.gender, 0.5)
    views = None
    for stale in ("views.json", "multiview_params.json"):
        (work / stale).unlink(missing_ok=True)
    if args.ai_turnaround:
        from fit import multiview
        try:
            sheet = work / "turnaround_raw.png"
            if not (args.reuse_ai and sheet.exists()):
                sheet = multiview.generate(work, log=log)
            else:
                log("    reusing the existing AI turnaround sheet")
            views = multiview.split(sheet, work)
            log(f"    AI turnaround: 3 views (side faces {'left' if views['side']['yaw'] < 0 else 'right'})")
        except Exception as e:  # never fail the avatar because the optional step failed
            log(f"    AI turnaround failed ({e}); single-photo fit instead")
            views = None
    res, pv, pk, obs, faces, V = body.choose_and_fit(work, gender_init=min(max(g0, 0.02), 0.98))
    if views:
        mv = multiview.fit(work, views, gender_init=min(max(g0, 0.02), 0.98))
        log("    3-view fit: " + ", ".join(f"{k} in={v['inside']:.5f} cov={v['coverage']:.5f}" for k, v in mv["multiview"].items()))
        res.update({k: mv[k] for k in ("phenotype", "local_changes", "multiview")})
        res["mv_pose_rotvec"] = mv["pose_rotvec"]
    if args.gender:
        res["phenotype"]["gender"] = g0
    mode = "stylized" if res["stylized"] else "realistic"
    hr = res.get("head_ratio")
    log(f"    mode={mode} head/height={'n/a' if hr is None else f'{hr:.2f}'} kp_err={res['kp_error']:.5f} coverage={res['coverage']:.5f}")
    rgba = cv2.cvtColor(cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
    cv2.imwrite(str(work / "body_fit.png"), cv2.cvtColor(body.render_overlay(rgba, pv, faces, V, pk, obs), cv2.COLOR_RGB2BGR))

    json.dump(res, open(work / "body_params.json", "w"), indent=1)
    params = {"phenotype": res["phenotype"], "local_changes": res["local_changes"],
              "bone_scale": res.get("bone_scale", {})}
    from fit import face
    if prep.face is not None and not res["stylized"]:
        log("3/6 face fit (478 landmarks → Anny face shape)")
        params["local_changes"].update(face.fit(work, res))
    else:
        log("3/6 face fit skipped (" + ("stylized/cartoon body" if prep.face is not None else "no face detected") + ")")
    json.dump(params, open(work / "params.json", "w"), indent=1)

    log("4/6 texture (photo → UV)")
    from fit import texture
    back = work / "back_cutout.png"
    if back.exists():
        back.unlink()
    if views:
        tmeta = texture.bake_multiview(work, params, {"multiview": res["multiview"], "pose_rotvec": res["mv_pose_rotvec"]})
    if args.ai_backview and not views:
        from fit import backview
        try:
            backview.generate(work, log=log)
        except Exception as e:  # never fail the whole avatar because the optional step failed
            log(f"    AI back view failed ({e}); falling back to geometric fill")
    if not views:
        tmeta = texture.bake(work, params, res)
    log(f"    from {'AI 3 views' if tmeta.get('ai_turnaround') else 'photo'}{' + AI back view' if tmeta.get('ai_backview') else ''}: {tmeta['coverage']:.0%} of the UV atlas; rest inpainted")

    log("    hair / eyebrows / eyelashes (MakeHuman CC0 proxies)")
    from fit import hair as hairmod
    hinfo = hairmod.analyse(work, gender_hint=GENDER.get(args.gender))
    style = hinfo["style"] if args.hair == "auto" else args.hair
    if views and args.hair == "auto":  # back / side views show what the front can't (ponytail, bun)
        vstyle, why = multiview.hair_style_from_views(work)
        if vstyle and style not in ("long01", "bob01", "bob02", "afro01", "none"):
            style, hinfo["reason"] = vstyle, why
    log(f"    hair={style} ({'auto: ' + str(hinfo['reason']) if args.hair == 'auto' else 'user choice'})")
    hair_rgb = hinfo["hair_rgb"] or tmeta.get("hair") or [60, 45, 35]
    brow_rgb = hinfo["brow_rgb"] or [c * 0.6 for c in hair_rgb]
    specs = []
    from fit.proxies import ASSETS, load as load_proxy
    for kind, name, rgb in (("hair", style, hair_rgb), ("eyebrows", "eyebrow001", brow_rgb),
                            ("eyelashes", "eyelashes01", [25, 20, 18])):
        if name == "none":
            continue
        src = load_proxy(kind, name).texture
        tex = hairmod.tint_texture(src, rgb, work / f"{kind}_{name}.png") if src else None
        specs.append({"kind": kind, "name": name, "texture": str(tex) if tex else None})
    from fit import shoes as shoesmod
    sinfo = shoesmod.analyse(work, tmeta.get("skin"))
    shoe = sinfo["style"] if args.shoes == "auto" else args.shoes
    log(f"    shoes={shoe} ({'auto: ' + sinfo['reason'] if args.shoes == 'auto' else 'user choice'})")
    if shoe != "none":
        src = load_proxy("clothes", shoe).texture
        tex = src
        if args.shoes == "auto" and sinfo.get("rgb"):  # nudge the texture towards the photo's shoe colour
            tex = hairmod.tint_texture(src, sinfo["rgb"], work / f"clothes_{shoe}.png", strength=0.6)
        specs.append({"kind": "clothes", "name": shoe, "texture": str(tex)})
    if args.glasses != "off":
        specs.append({"kind": "glasses", "name": args.glasses,
                      "color": [int(c) for c in args.glasses_color.split(",")]})
        log(f"    glasses={args.glasses}")
    json.dump(specs, open(work / "proxies.json", "w"), indent=1)

    log("5/6 T-pose export")
    npz = work / "anny_tpose.npz"
    subprocess.run([sys.executable, str(HERE / "export_anny.py"), "--params", str(work / "params.json"),
                    "--proxies", str(work / "proxies.json"),
                    "--out", str(npz)], cwd=HERE, check=True, stdout=subprocess.DEVNULL)

    log("6/6 VRM build (Blender)")
    env = {"BLENDER_USER_RESOURCES": str(ROOT / "build" / "blender_user"), "PATH": "/usr/bin:/bin"}
    r = subprocess.run([args.blender, "-b", "--python", str(HERE / "build_vrm.py"), "--", str(npz), str(out), str(work / "texture.json")],
                       env=env, capture_output=True, text=True)
    if "EXPORT" not in r.stdout or r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        raise SystemExit("VRM build failed")
    log(f"done in {time.time() - t0:.0f}s → {out.name}.vrm0.vrm / {out.name}.vrm1.vrm")


if __name__ == "__main__":
    main()
