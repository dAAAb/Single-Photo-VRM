"""Tiny orthographic z-buffer rasterizer (numpy) — shading + triangle-id buffer for QA and
landmark correspondence. Camera looks along +Y (Anny faces -Y); image x = +X, image y = -Z."""
import numpy as np


def rasterize(V, F, colors, center, scale, size=512, light=(0.3, -1.0, 0.5)):
    """V (N,3) world, F (M,3), colors (M,3) per face. Returns rgb (size,size,3), tri_id (size,size)."""
    P = np.stack([(V[:, 0] - center[0]) * scale + size / 2, -(V[:, 2] - center[2]) * scale + size / 2], 1)
    depth = V[:, 1]
    rgb = np.full((size, size, 3), 235, np.float32)
    zbuf = np.full((size, size), np.inf, np.float32)
    tid = -np.ones((size, size), np.int32)
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.asarray(light, np.float32)
    L /= np.linalg.norm(L)
    shade = 0.35 + 0.65 * np.clip(n @ L, 0, 1)  # lambert; L points from the surface toward the light
    front = n[:, 1] < 0
    for i in np.where(front)[0]:
        a, b, c = P[F[i]]
        x0, x1 = int(max(0, np.floor(min(a[0], b[0], c[0])))), int(min(size - 1, np.ceil(max(a[0], b[0], c[0]))))
        y0, y1 = int(max(0, np.floor(min(a[1], b[1], c[1])))), int(min(size - 1, np.ceil(max(a[1], b[1], c[1]))))
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / d
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / d
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        z = w0 * depth[F[i, 0]] + w1 * depth[F[i, 1]] + w2 * depth[F[i, 2]]
        yy, xx = ys[inside].astype(int), xs[inside].astype(int)
        zz = z[inside]
        closer = zz < zbuf[yy, xx]
        yy, xx, zz = yy[closer], xx[closer], zz[closer]
        zbuf[yy, xx] = zz
        tid[yy, xx] = i
        rgb[yy, xx] = colors[i] * shade[i]
    return np.clip(rgb, 0, 255).astype(np.uint8), tid, P


def barycentric(p, tri2d):
    a, b, c = tri2d
    d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    w0 = ((b[1] - c[1]) * (p[0] - c[0]) + (c[0] - b[0]) * (p[1] - c[1])) / d
    w1 = ((c[1] - a[1]) * (p[0] - c[0]) + (a[0] - c[0]) * (p[1] - c[1])) / d
    return np.array([w0, w1, 1 - w0 - w1])
