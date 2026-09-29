import torch, anny, trimesh, numpy as np
OBJ = "../third_party/anny/src/anny/data/mpfb2/3dobjs/base.obj"
groups, cur = {}, None
for line in open(OBJ):
    if line.startswith("g "):
        cur = line.split()[1]
    elif line.startswith("f ") and cur:
        groups.setdefault(cur, []).append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
for g in ("helper-upper-teeth", "helper-lower-teeth", "helper-tongue"):
    fs = groups[g]; vs = sorted({v for f in fs for v in f})
    print(g, "faces", len(fs), "verts", len(vs), "sides", {len(f) for f in fs})
m = anny.Anny(facial_actions="all", topology="anny-full").to(dtype=torch.float32)
P = torch.eye(4)[None, None].repeat(1, m.bone_count, 1, 1)
run = lambda fa={}: m(pose_parameters=P, facial_actions=fa)["vertices"][0].detach().numpy()
v0 = run()
for name in ["jawOpen", "jawLeft", "jawForward", "mouthClose", "tongueOut"]:
    d = np.linalg.norm(run({name: 1.0}) - v0, axis=1)
    for g in ("helper-upper-teeth", "helper-lower-teeth"):
        vs = sorted({v for f in groups[g] for v in f})
        print(f"  {name:10s} {g:20s} moved {int((d[vs] > 1e-4).sum()):3d}/{len(vs)} max {d[vs].max():.4f}")
def tri(fs): return [t for f in fs for t in ([f] if len(f) == 3 else [[f[0], f[1], f[2]], [f[0], f[2], f[3]]])]
for g in ("helper-upper-teeth", "helper-lower-teeth"):
    vs = sorted({v for f in groups[g] for v in f}); b = v0[vs]
    print(g, "center", np.round(b.mean(0), 3), "size", np.round(b.max(0) - b.min(0), 3))
trimesh.Trimesh(v0, tri(groups["helper-upper-teeth"] + groups["helper-lower-teeth"]), process=False).export("/tmp/teeth.ply")
