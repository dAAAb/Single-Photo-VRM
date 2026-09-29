"""Procedural glasses (frame only), placed from MediaPipe landmarks mapped onto the fitted head.

Landmarks (MediaPipe face mesh): eye corners 33/133 (subject's right eye), 362/263 (left eye),
eyelids 159/145 and 386/374, nose bridge 168, face sides 234 (right) / 454 (left).
Everything is generated in Anny coordinates (z up, face towards -Y) and rigidly skinned to "head".
"""
import numpy as np

from . import face_corr


def _lm(V, corr, i):
    return (V[corr["tri"][i]] * corr["bary"][i][:, None]).sum(0)


def _tube(path, radius, sides=6, closed=True):
    """Thin tube along a polyline → (verts, tris)."""
    path = np.asarray(path, np.float32)
    n = len(path)
    verts, tris = [], []
    for k in range(n):
        t = path[(k + 1) % n] - path[k - 1] if closed else path[min(k + 1, n - 1)] - path[max(k - 1, 0)]
        t /= np.linalg.norm(t) + 1e-9
        a = np.cross(t, [0, 1, 0]) if abs(t[1]) < 0.9 else np.cross(t, [1, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(t, a)
        for j in range(sides):
            ang = 2 * np.pi * j / sides
            verts.append(path[k] + radius * (np.cos(ang) * a + np.sin(ang) * b))
    segs = n if closed else n - 1
    for k in range(segs):
        k2 = (k + 1) % n
        for j in range(sides):
            j2 = (j + 1) % sides
            a0, a1, b0, b1 = k * sides + j, k * sides + j2, k2 * sides + j, k2 * sides + j2
            tris += [[a0, b0, a1], [a1, b0, b1]]
    return np.array(verts, np.float32), np.array(tris, np.int32)


def build(V: np.ndarray, style: str = "round"):
    """V: fitted T-pose anny-full vertices. Returns (verts, tris)."""
    corr = face_corr.build()
    L = lambda i: _lm(V, corr, i)
    parts = []
    fwd = np.array([0, -1, 0], np.float32)
    for outer, inner, top, bot in ((33, 133, 159, 145), (263, 362, 386, 374)):
        c = (L(outer) + L(inner)) / 2
        w = np.linalg.norm(L(outer) - L(inner)) * 1.45
        h = w * (0.78 if style == "round" else 0.62)
        c = c + fwd * 0.012 + np.array([0, 0, 0.002])
        ang = np.linspace(0, 2 * np.pi, 28, endpoint=False)
        if style == "round":
            ring = [c + np.array([np.cos(a) * w / 2, 0, np.sin(a) * h / 2]) for a in ang]
        else:  # rounded rectangle (superellipse)
            ring = [c + np.array([np.sign(np.cos(a)) * abs(np.cos(a)) ** 0.4 * w / 2, 0,
                                  np.sign(np.sin(a)) * abs(np.sin(a)) ** 0.4 * h / 2]) for a in ang]
        parts.append(("lens", ring, c, w))
    (_, rR, cR, wR), (_, rL, cL, wL) = parts
    geo = [_tube(rR, 0.0016), _tube(rL, 0.0016)]
    bridge_in_R = cR + np.array([wR / 2 * 0.95 * np.sign(cL[0] - cR[0]), 0, 0.004])
    bridge_in_L = cL + np.array([wL / 2 * 0.95 * np.sign(cR[0] - cL[0]), 0, 0.004])
    mid = (bridge_in_R + bridge_in_L) / 2 + np.array([0, -0.002, 0.003])
    geo.append(_tube([bridge_in_R, mid, bridge_in_L], 0.0014, closed=False))
    for c, w, side_lm, sgn in ((cR, wR, 234, np.sign(cR[0] - cL[0])), (cL, wL, 454, np.sign(cL[0] - cR[0]))):
        hinge = c + np.array([sgn * w / 2, 0, 0.004])
        ear = L(side_lm)
        ear = np.array([ear[0] + sgn * 0.004, ear[1] + 0.035, hinge[2] - 0.004])  # back over the ear
        geo.append(_tube([hinge, (hinge + ear) / 2 + np.array([sgn * 0.003, 0, 0]), ear], 0.0014, closed=False))
    verts, tris, off = [], [], 0
    for v, t in geo:
        verts.append(v)
        tris.append(t + off)
        off += len(v)
    return np.concatenate(verts), np.concatenate(tris)
