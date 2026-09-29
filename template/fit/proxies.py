"""MakeHuman CC0 proxies (hair, eyebrows, eyelashes) fitted onto Anny.

A .mhclo binds each proxy vertex to 3 base-mesh (hm08) vertices with barycentric weights plus a
scaled offset. Anny's "anny-full" topology *is* hm08, so proxies follow the fitted shape exactly,
inherit skin weights from their reference vertices, and get the 52 ARKit shape keys for free
(eyelashes blink, eyebrows raise).
Coordinates: Anny = 0.1 * (x, -z, y) of MakeHuman (verified to 1e-8 on the template).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

ASSETS = Path(__file__).resolve().parents[2] / "third_party" / "makehuman_assets" / "system"


def to_mh(v):
    return np.stack([v[..., 0] * 10, v[..., 2] * 10, -v[..., 1] * 10], -1)


def from_mh(v):
    return np.stack([v[..., 0] * 0.1, -v[..., 2] * 0.1, v[..., 1] * 0.1], -1)


@dataclass
class Proxy:
    name: str
    refs: np.ndarray      # (N,3) base vertex indices
    weights: np.ndarray   # (N,3)
    offsets: np.ndarray   # (N,3) MakeHuman axes
    scales: dict          # axis -> (v1, v2, den)
    faces: list           # list of vertex index lists (tris/quads)
    uv_faces: list
    uvs: np.ndarray
    texture: Path | None
    obj_verts: np.ndarray  # authored positions (MakeHuman units) for validation
    delete_verts: np.ndarray | None = None  # base vertices hidden under this proxy (e.g. feet in shoes)


def _ranges(tokens):
    """'4793 - 4846 4899 6391' → indices (MakeHuman writes ranges with spaced dashes)."""
    out, toks, i = [], [t for t in " ".join(tokens).replace("-", " - ").split()], 0
    while i < len(toks):
        if i + 2 < len(toks) and toks[i + 1] == "-":
            out.extend(range(int(toks[i]), int(toks[i + 2]) + 1))
            i += 3
        elif toks[i].isdigit():
            out.append(int(toks[i]))
            i += 1
        else:
            i += 1
    return out


def load(kind: str, name: str) -> Proxy:
    d = ASSETS / kind / name
    mhclo = next(d.glob("*.mhclo"))
    refs, weights, offsets, scales, obj_file = [], [], [], {}, None
    deleted = []
    in_verts = in_delete = False
    for line in open(mhclo, encoding="utf-8", errors="ignore"):
        s = line.split()
        if not s or s[0].startswith("#"):
            continue
        if not s[0][0].isdigit() and s[0] != "delete_verts":
            in_delete = False
        if s[0] in ("x_scale", "y_scale", "z_scale"):
            scales[s[0][0]] = (int(s[1]), int(s[2]), float(s[3]))
        elif s[0] == "obj_file":
            obj_file = d / s[1]
        elif s[0] == "verts":
            in_verts = True
        elif in_delete and s[0][0].isdigit():
            deleted.extend(_ranges(s))
        elif in_verts and s[0][0].isdigit():
            if len(s) >= 9:
                refs.append([int(x) for x in s[:3]])
                weights.append([float(x) for x in s[3:6]])
                offsets.append([float(x) for x in s[6:9]])
            elif len(s) == 1:  # exact vertex
                refs.append([int(s[0])] * 3)
                weights.append([1.0, 0.0, 0.0])
                offsets.append([0.0, 0.0, 0.0])
        elif s[0] == "delete_verts":  # numeric ranges (same line or following lines), not vertex data
            in_verts, in_delete = False, True
            deleted.extend(_ranges(s[1:]))
    ov, uv, faces, ufaces = [], [], [], []
    for line in open(obj_file, encoding="utf-8", errors="ignore"):
        s = line.split()
        if not s:
            continue
        if s[0] == "v":
            ov.append([float(x) for x in s[1:4]])
        elif s[0] == "vt":
            uv.append([float(x) for x in s[1:3]])
        elif s[0] == "f":
            faces.append([int(t.split("/")[0]) - 1 for t in s[1:]])
            ufaces.append([int(t.split("/")[1]) - 1 if "/" in t and t.split("/")[1] else 0 for t in s[1:]])
    tex = None
    mat = next(d.glob("*.mhmat"), None)
    if mat:
        for line in open(mat, encoding="utf-8", errors="ignore"):
            s = line.split()
            if len(s) >= 2 and s[0] == "diffuseTexture":
                cand = d / Path(s[1]).name
                tex = cand if cand.exists() else None
    return Proxy(name, np.array(refs), np.array(weights), np.array(offsets), scales, faces, ufaces,
                 np.array(uv, np.float32), tex, np.array(ov, np.float32), np.array(sorted(set(deleted)), np.int64))


def fit(p: Proxy, V_anny: np.ndarray) -> np.ndarray:
    """Proxy vertex positions (Anny coords) for base-mesh vertices V_anny (anny-full indexing)."""
    Vm = to_mh(V_anny)
    sc = np.ones(3)
    for i, ax in enumerate("xyz"):
        if ax in p.scales:
            a, b, den = p.scales[ax]
            sc[i] = abs(Vm[a, i] - Vm[b, i]) / den
    pos = (Vm[p.refs] * p.weights[..., None]).sum(1) + p.offsets * sc
    return from_mh(pos)


def delta(p: Proxy, D_anny: np.ndarray) -> np.ndarray:
    """Shape-key deltas for the proxy from base-mesh deltas (K, V, 3) → (K, N, 3)."""
    return (D_anny[:, p.refs] * p.weights[None, ..., None]).sum(2)


def skin(p: Proxy, w_idx: np.ndarray, w: np.ndarray, max_inf: int = 8):
    """Blend the reference vertices' skin weights."""
    N = len(p.refs)
    out_i = np.zeros((N, max_inf), np.int32)
    out_w = np.zeros((N, max_inf), np.float32)
    for n in range(N):
        acc = {}
        for r, bw in zip(p.refs[n], p.weights[n]):
            for bi, ww in zip(w_idx[r], w[r]):
                if ww > 0:
                    acc[int(bi)] = acc.get(int(bi), 0.0) + float(bw) * float(ww)
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:max_inf]
        tot = sum(v for _, v in top) or 1.0
        for j, (bi, ww) in enumerate(top):
            out_i[n, j], out_w[n, j] = bi, ww / tot
    return out_i, out_w


if __name__ == "__main__":
    import anny, torch
    m = anny.Anny(topology="anny-full").to(dtype=torch.float32)
    V = m.template_vertices.numpy()
    for kind in ("hair", "eyebrows", "eyelashes"):
        for d in sorted((ASSETS / kind).iterdir()):
            if not d.is_dir():
                continue
            p = load(kind, d.name)
            got = fit(p, V)
            err = np.abs(to_mh(got) - p.obj_verts).max() if len(p.obj_verts) == len(got) else float("nan")
            print(f"{kind:10s} {d.name:12s} verts={len(got):6d} faces={len(p.faces):6d} max_err_vs_obj={err:.4f} tex={p.texture.name if p.texture else None}")
