"""Anny → T-pose template data (mesh, UVs, skin weights, bones, 52 ARKit deltas) for the Blender VRM builder.

Run with the template venv:  .venv/bin/python export_anny.py [--out ../build/anny_tpose.npz]
"""
import argparse
import json

import anny
import numpy as np
import roma
import torch

ARKIT_52 = json.load(open("arkit52.json"))
BASE_OBJ = anny.__file__.rsplit("/", 1)[0] + "/data/mpfb2/3dobjs/base.obj"
TEETH_GROUPS = ("helper-upper-teeth", "helper-lower-teeth")


def obj_group_tris(path, group_names):
    """Triangulated (vertex, uv) index lists of the given groups in the MakeHuman base mesh (CC0)."""
    vs, uvs, cur = [], [], None
    for line in open(path):
        if line.startswith("g "):
            cur = line.split()[1]
        elif line.startswith("f ") and cur in group_names:
            toks = [t.split("/") for t in line.split()[1:]]
            v = [int(t[0]) - 1 for t in toks]
            u = [int(t[1]) - 1 for t in toks]
            for a, b, c in ((0, 1, 2), (0, 2, 3))[: len(v) - 2]:
                vs.append([v[a], v[b], v[c]])
                uvs.append([u[a], u[b], u[c]])
    return np.array(vs, np.int32), np.array(uvs, np.int32)

# Anny bone → VRM humanoid bone. Anny bones not listed stay as non-humanoid (twist / helper) bones.
VRM_BONES = {
    "root": "hips", "spine05": "spine", "spine03": "chest", "spine01": "upperChest",
    "neck01": "neck", "head": "head", "eye.L": "leftEye", "eye.R": "rightEye",
}
for s, S in (("L", "left"), ("R", "right")):
    VRM_BONES.update({
        f"clavicle.{s}": f"{S}Shoulder", f"upperarm01.{s}": f"{S}UpperArm",
        f"lowerarm01.{s}": f"{S}LowerArm", f"wrist.{s}": f"{S}Hand",
        f"upperleg01.{s}": f"{S}UpperLeg", f"lowerleg01.{s}": f"{S}LowerLeg", f"foot.{s}": f"{S}Foot",
        f"finger1-1.{s}": f"{S}ThumbMetacarpal", f"finger1-2.{s}": f"{S}ThumbProximal", f"finger1-3.{s}": f"{S}ThumbDistal",
    })
    for n, F in ((2, "Index"), (3, "Middle"), (4, "Ring"), (5, "Little")):
        for seg, SEG in ((1, "Proximal"), (2, "Intermediate"), (3, "Distal")):
            VRM_BONES[f"finger{n}-{seg}.{s}"] = f"{S}{F}{SEG}"


def rot_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Minimal rotation matrix taking direction a onto direction b."""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if np.linalg.norm(v) < 1e-8:
        return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../build/anny_tpose.npz")
    args = ap.parse_args()

    # "anny-full" keeps MakeHuman helper vertices, which include the teeth; Face Units move the lower teeth.
    model = anny.Anny(facial_actions="all", topology="anny-full").to(dtype=torch.float32)
    assert list(model.facial_action_labels) == ARKIT_52 or set(model.facial_action_labels) == set(ARKIT_52)
    labels = list(model.bone_labels)
    idx = {n: i for i, n in enumerate(labels)}
    parents = [int(p) for p in model.bone_parents]
    B = len(labels)

    ident = torch.eye(4)[None, None].repeat(1, B, 1, 1)
    rest = model(pose_parameters=ident)
    rest_poses = rest["bone_poses"][0].numpy()  # (B,4,4) world, rest (A-pose)
    head = rest_poses[:, :3, 3]

    # World-space rotation per bone to reach a VRM T-pose (arms along ±X, legs straight down).
    delta = [None] * B
    X = np.array([1.0, 0, 0])
    DOWN = np.array([0, 0, -1.0])
    for s, sign in (("L", 1.0), ("R", -1.0)):
        for bone, child in ((f"upperarm01.{s}", f"lowerarm01.{s}"), (f"lowerarm01.{s}", f"wrist.{s}"),
                            (f"wrist.{s}", f"finger3-1.{s}")):
            delta[idx[bone]] = rot_between(head[idx[child]] - head[idx[bone]], sign * X)
        for bone, child in ((f"upperleg01.{s}", f"lowerleg01.{s}"), (f"lowerleg01.{s}", f"foot.{s}")):
            delta[idx[bone]] = rot_between(head[idx[child]] - head[idx[bone]], DOWN)
    for i in range(B):  # descendants inherit the nearest ancestor's world rotation
        if delta[i] is None:
            delta[i] = delta[parents[i]] if parents[i] >= 0 else np.eye(3)

    abs_orient = np.stack([delta[i] @ rest_poses[i, :3, :3] for i in range(B)])
    pose = torch.eye(4)[None, None].repeat(1, B, 1, 1)
    pose[0, :, :3, :3] = torch.from_numpy(abs_orient).float()
    pose[0, 0, :3, 3] = torch.from_numpy(rest_poses[0, :3, 3]).float()

    def run(fa=None):
        o = model(pose_parameters=pose, facial_actions=fa or {}, pose_parameterization="world-orient")
        return o["vertices"][0].numpy(), o["bone_poses"][0].numpy()

    verts, poses = run()
    heads = poses[:, :3, 3]
    # VRM: feet on the ground (y=0 in glTF = z=0 here). Anny's origin is at the pelvis.
    ground = np.array([0, 0, verts[:, 2].min()], np.float32)
    # sanity: T-pose arms level, legs vertical
    for s in "LR":
        arm = heads[idx[f"wrist.{s}"]] - heads[idx[f"upperarm01.{s}"]]
        leg = heads[idx[f"foot.{s}"]] - heads[idx[f"upperleg01.{s}"]]
        print(f"{s}: arm dir {np.round(arm / np.linalg.norm(arm), 3)}  leg dir {np.round(leg / np.linalg.norm(leg), 3)}")

    deltas = np.zeros((len(ARKIT_52), *verts.shape), np.float32)
    for k, name in enumerate(ARKIT_52):
        deltas[k] = run({name: 1.0})[0] - verts
    verts = verts - ground
    heads = heads - ground

    # Tails: first child head, else extend along parent direction.
    children = {i: [j for j in range(B) if parents[j] == i] for i in range(B)}
    tails = np.zeros_like(heads)
    for i in range(B):
        kids = children[i]
        pref = [j for j in kids if labels[j].startswith(("lowerarm", "wrist", "lowerleg", "foot", "upperarm02", "lowerarm02", "upperleg02", "lowerleg02", "spine", "neck", "head", "finger", "toe"))]
        if labels[i] == "root":
            tails[i] = heads[idx["spine05"]]
        elif labels[i] in ("head",):
            tails[i] = heads[i] + np.array([0, 0, 0.12])
        elif labels[i].startswith("eye"):
            tails[i] = heads[i] + np.array([0, -0.02, 0])
        elif pref:
            tails[i] = heads[pref[0]]
        elif kids:
            tails[i] = heads[kids[0]]
        else:
            p = parents[i]
            d = heads[i] - heads[p]
            tails[i] = heads[i] + d / (np.linalg.norm(d) + 1e-9) * max(0.02, 0.6 * np.linalg.norm(d))
        if np.linalg.norm(tails[i] - heads[i]) < 1e-3:
            tails[i] = heads[i] + np.array([0, 0, 0.02])

    uv = model.texture_coordinates.numpy().astype(np.float32)
    body_faces = np.asarray(model.faces, dtype=np.int32)
    teeth_faces, teeth_uv = obj_group_tris(BASE_OBJ, TEETH_GROUPS)
    faces = np.concatenate([body_faces, teeth_faces])
    uv_idx = np.concatenate([np.asarray(model.face_texture_coordinate_indices, dtype=np.int32), teeth_uv])
    w_idx = model.vertex_bone_indices.numpy().astype(np.int32)
    w = model.vertex_bone_weights.numpy().astype(np.float32)

    # Drop helper vertices that no face references (tights, skirt, hair helpers, joints, …).
    used = np.unique(faces)
    remap = -np.ones(len(verts), np.int64)
    remap[used] = np.arange(len(used))
    faces = remap[faces].astype(np.int32)
    verts, deltas, w_idx, w = verts[used], deltas[:, used], w_idx[used], w[used]
    teeth = np.zeros(len(used), bool)
    teeth[np.unique(faces[len(body_faces):])] = True

    np.savez_compressed(
        args.out, verts=verts.astype(np.float32), faces=faces, uv=uv, uv_idx=uv_idx,
        w_idx=w_idx, w=w, heads=heads.astype(np.float32), tails=tails.astype(np.float32),
        parents=np.array(parents, np.int32), labels=np.array(labels), arkit=np.array(ARKIT_52),
        deltas=deltas, vrm_map=np.array(json.dumps(VRM_BONES)), teeth=teeth,
    )
    print(f"wrote {args.out}: {len(verts)} verts, {len(faces)} faces, {B} bones, {len(ARKIT_52)} shapes;"
          f" height {verts[:, 2].max() - verts[:, 2].min():.3f} m, max delta {np.abs(deltas).max():.4f}")


if __name__ == "__main__":
    main()
