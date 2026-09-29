import torch, anny, trimesh, numpy as np
m = anny.Anny(facial_actions="all").to(dtype=torch.float32)
P = torch.eye(4)[None, None].repeat(1, m.bone_count, 1, 1)
def run(fa):
    out = m(pose_parameters=P, facial_actions=fa)
    return out["vertices"][0].detach().numpy()
F = m.faces.numpy() if hasattr(m.faces, "numpy") else np.asarray(m.faces)
v0 = run({})
tm = trimesh.Trimesh(v0, F, process=False)
comps = tm.split(only_watertight=False)
print("components:", len(comps))
for c in sorted(comps, key=lambda c: -len(c.vertices))[:12]:
    b = c.bounds
    print(f"  verts={len(c.vertices):6d} center={np.round(c.centroid,3)} size={np.round(b[1]-b[0],3)}")
print("height:", np.round(v0[:,1].max()-v0[:,1].min(),3), "y-range", v0[:,1].min(), v0[:,1].max(), "z-range", v0[:,2].min(), v0[:,2].max())
for name in ["jawOpen", "tongueOut", "eyeBlinkLeft", "eyeLookUpLeft", "mouthSmileLeft", "cheekPuff"]:
    d = np.linalg.norm(run({name: 1.0}) - v0, axis=1)
    idx = np.where(d > 1e-4)[0]
    print(f"{name:15s} moved={len(idx):5d} max={d.max():.4f} centroid={np.round(v0[idx].mean(0),3) if len(idx) else None}")
# weights for eye bones
W = getattr(m, "vertex_bone_weights", None)
print("attrs:", [a for a in dir(m) if "weight" in a.lower() or "skin" in a.lower()][:20])
trimesh.Trimesh(v0, F, process=False).export("/tmp/anny_neutral.ply")
trimesh.Trimesh(run({"jawOpen":0.8,"tongueOut":1.0,"eyeBlinkLeft":1.0}), F, process=False).export("/tmp/anny_expr.ply")
