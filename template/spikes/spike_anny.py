"""Spike: does Anny's built-in face (faceunits01) cover ARKit 52 + eyes/teeth/tongue?"""
import json, sys, time
import torch, anny


ARKIT_52 = [l.strip(" ',") for l in open("../../viewer/src/arkit.ts").read().split("ARKIT_52 = [")[1].split("]")[0].replace("\n", " ").split(",") if l.strip(" ',")]
ARKIT_52 = [a.strip().strip("'") for a in ARKIT_52 if a.strip().strip("'")]
assert len(ARKIT_52) == 52, len(ARKIT_52)

t = time.time()
m = anny.Anny(facial_actions="all").to(dtype=torch.float32)
print(f"model built in {time.time()-t:.1f}s")
fa = list(m.facial_action_labels)
print("facial actions:", len(fa))
missing = [a for a in ARKIT_52 if a not in fa]
extra = [a for a in fa if a not in ARKIT_52]
print("missing ARKit:", missing)
print("extra:", extra)
print("bones:", m.bone_count)
print("bone labels:", list(m.bone_labels))
print("phenotypes:", list(m.phenotype_labels))
print("verts:", m.template_vertices.shape if hasattr(m, "template_vertices") else "?", "faces:", m.faces.shape)
