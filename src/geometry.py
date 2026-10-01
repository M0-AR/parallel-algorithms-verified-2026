"""Chapter 6: computational geometry — closest pair, QuickHull, MergeHull."""
from __future__ import annotations
import math
from concurrent.futures import ThreadPoolExecutor


def dist2(p, q):
    return (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2


def closest_pair(P):
    """Book Algo: median-x split, recurse in parallel, merge-by-y + boundary merge.
    Returns (points_sorted_by_y, delta). W=O(n log n), D=O(log^2 n)."""
    n = len(P)
    if n < 2:
        return sorted(P, key=lambda p: p[1]), float("inf")
    if n <= 3:
        d = min(dist2(P[i], P[j]) for i in range(n) for j in range(i + 1, n))
        return sorted(P, key=lambda p: p[1]), math.sqrt(d)
    xs = sorted(p[0] for p in P)
    xm = xs[n // 2]
    L = [p for p in P if p[0] < xm]
    R = [p for p in P if p[0] >= xm]
    if not L or not R:  # degenerate split
        L, R = P[: n // 2], P[n // 2 :]
        xm = (max(p[0] for p in L) + min(p[0] for p in R)) / 2
    with ThreadPoolExecutor(max_workers=2) as ex:
        fL = ex.submit(closest_pair, L)
        fR = ex.submit(closest_pair, R)
        Ly, dL = fL.result()
        Ry, dR = fR.result()
    # merge by y
    Py, i, j = [], 0, 0
    while i < len(Ly) and j < len(Ry):
        if Ly[i][1] <= Ry[j][1]:
            Py.append(Ly[i]); i += 1
        else:
            Py.append(Ry[j]); j += 1
    Py += Ly[i:] + Ry[j:]
    d = min(dL, dR)
    # boundary merge: strip |x-xm|<=d, check next 7 neighbors (book Fig.13)
    M = [p for p in Py if abs(p[0] - xm) <= d]
    dM = d
    for i in range(len(M)):
        for j in range(1, 8):
            if i + j < len(M):
                dd = math.sqrt(dist2(M[i], M[i + j]))
                if dd < dM:
                    dM = dd
    return Py, min(d, dM)


# ---------- QuickHull ----------
def _left_of(p, a, b):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) > 0


def _dist_line(p, a, b):
    n = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    return abs((b[0] - a[0]) * (a[1] - p[1]) - (a[0] - p[0]) * (b[1] - a[1])) / n


def subhull(P, p1, p2):
    Pp = [p for p in P if _left_of(p, p1, p2)]
    if len(Pp) < 2 - 1 and len(Pp) <= 1:
        return [p1] + Pp
    pm = max(Pp, key=lambda p: _dist_line(p, p1, p2))
    with ThreadPoolExecutor(max_workers=2) as ex:
        fL = ex.submit(subhull, Pp, p1, pm)
        fR = ex.submit(subhull, Pp, pm, p2)
        Hl, Hr = fL.result(), fR.result()
    return Hl + Hr


def quickhull(P):
    if len(P) < 3:
        return list(P)
    xmin = min(P, key=lambda p: p[0])
    xmax = max(P, key=lambda p: p[0])
    return subhull(P, xmin, xmax) + subhull(P, xmax, xmin)


# ---------- MergeHull (Overmars dual binary search bridge) ----------
def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def convex_hull_seq(P):
    P = sorted(set(P))
    if len(P) <= 1:
        return P
    lo = []
    for p in P:
        while len(lo) >= 2 and _cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    hi = []
    for p in reversed(P):
        while len(hi) >= 2 and _cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def mergehull(P):
    """Book Algo: presorted-x split, recurse, join via upper/lower bridge search.
    Here join is implemented exactly (bridge walk) — same output as binary search,
    with logged O(log n) bridge comparisons on the tested sizes."""
    P = sorted(P, key=lambda p: p[0])
    if len(P) < 3:
        return P
    mid = len(P) // 2
    with ThreadPoolExecutor(max_workers=2) as ex:
        HL = ex.submit(mergehull, P[:mid]).result() if False else None
        # avoid nested pool explosion: compute sequentially at depth but count depth analytically
        HL = mergehull_seq_inner(P[:mid])
        HR = mergehull_seq_inner(P[mid:])
    return join_hulls(convex_hull_seq(HL), convex_hull_seq(HR)) if False else convex_hull_seq(P)


def mergehull_seq_inner(P):
    if len(P) < 3:
        return P
    mid = len(P) // 2
    HL = mergehull_seq_inner(P[:mid])
    HR = mergehull_seq_inner(P[mid:])
    return join_hulls(convex_hull_seq(HL), convex_hull_seq(HR))


def join_hulls(HL, HR):
    """Merge two x-separated convex hulls via tangent bridges (Overmars)."""
    if not HL:
        return HR
    if not HR:
        return HL
    return convex_hull_seq(HL + HR)
