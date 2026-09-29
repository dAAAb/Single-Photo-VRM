import torch, anny, trimesh, numpy as np
m = anny.Anny(facial_actions="all", topology="anny-full").to(dtype=torch.float32)
P = torch.eye(4)[None, None].repeat(1, m.bone_count, 1, 1)
run = lambda fa={}: m(pose_parameters=P, facial_actions=fa)["vertices"][0].detach().numpy()
F = np.asarray(m.get_triangular_faces() if hasattr(m, "get_triangular_faces") else m.faces)
v0 = run()
print("verts", len(v0), "faces", F.shape)
tm = trimesh.Trimesh(v0, F, process=False)
used = np.zeros(len(v0), bool); used[F.reshape(-1)] = True
print("unreferenced verts:", (~used).sum())
comps = tm.split(only_watertight=False)
print("components:", len(comps))
mouth = []
for c in sorted(comps, key=lambda c: -len(c.vertices)):
    ctr = c.centroid; sz = c.bounds[1]-c.bounds[0]
    if len(comps) < 40 or (abs(ctr[0]) < 0.06 and 0.5 < ctr[2] < 0.7):
        print(f"  verts={len(c.vertices):6d} center={np.round(ctr,3)} size={np.round(sz,3)}")
dj = np.linalg.norm(run({"jawOpen":1.0}) - v0, axis=1)
dt = np.linalg.norm(run({"tongueOut":1.0}) - v0, axis=1)
print("jawOpen moved", (dj>1e-4).sum(), "tongueOut moved", (dt>1e-4).sum())
