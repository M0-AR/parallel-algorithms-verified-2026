"""Chapter 5: sorting — parallel QuickSort, sample sort, radix sort (counting/stable)."""
from __future__ import annotations
import math
import random
from concurrent.futures import ThreadPoolExecutor
from .primitives import plus_scan
from .work_depth import Cost


def quicksort_seq(A):
    if len(A) <= 1:
        return list(A)
    p = A[len(A) // 2]
    L = [a for a in A if a < p]
    E = [a for a in A if a == p]
    G = [a for a in A if a > p]
    return quicksort_seq(L) + E + quicksort_seq(G)


def parallel_quicksort(A, depth_limit: int = 4, seed: int = 0):
    """Book Algo quicksort with rand pivot + parallel-do on L,G. Depth_limit emulates P."""
    rng = random.Random(seed)
    if len(A) <= 1:
        return list(A)
    if depth_limit <= 0 or len(A) < 2048:
        return quicksort_seq(A)
    p = A[rng.randrange(len(A))]
    L = [a for a in A if a < p]
    E = [a for a in A if a == p]
    G = [a for a in A if a > p]
    with ThreadPoolExecutor(max_workers=2) as ex:
        fL = ex.submit(parallel_quicksort, L, depth_limit - 1, rng.randrange(1 << 30))
        fG = ex.submit(parallel_quicksort, G, depth_limit - 1, rng.randrange(1 << 30))
        L, G = fL.result(), fG.result()
    return L + E + G


def sample_sort(A, nproc: int = 8, oversample: int = 8, seed: int = 0):
    """Blelloch et al. sample sort: sp candidates -> p-1 splitters -> bucket -> seq sort."""
    rng = random.Random(seed)
    n = len(A)
    if n <= 1:
        return list(A)
    s = max(1, oversample)
    cand = [A[rng.randrange(n)] for _ in range(min(n, s * nproc))]
    cand.sort()
    splitters = [cand[(i + 1) * len(cand) // nproc] for i in range(nproc - 1)] if len(cand) >= nproc else sorted(set(cand))[: nproc - 1]
    buckets = [[] for _ in range(len(splitters) + 1)]
    import bisect
    for a in A:
        buckets[bisect.bisect_right(splitters, a)].append(a)

    def sort_bucket(b):
        b.sort()
        return b

    with ThreadPoolExecutor(max_workers=nproc) as ex:
        buckets = list(ex.map(sort_bucket, buckets))
    out = []
    for b in buckets:
        out.extend(b)
    return out


def _counting_rank_step(A, bit):
    flags = [((a >> bit) & 1) for a in A]
    notflags = [1 - b for b in flags]
    R0 = plus_scan(notflags) + [0]  # exclusive; plus_scan len n
    R0 = plus_scan(notflags)
    s0 = sum(notflags)
    from .primitives import plus_scan as ps
    R1 = ps(flags)
    R = [R0[j] if flags[j] == 0 else R1[j] + s0 for j in range(len(A))]
    B = [None] * len(A)
    for j in range(len(A)):
        B[R[j]] = A[j]
    return B


def radix_sort(A, b: int = 32):
    """Book Algo radix_sort: b 1-bit stable counting passes. W=O(bn), D=O(b log n)."""
    A = list(A)
    assert all(a >= 0 for a in A), "radix here for non-negative ints (floats converted by caller)"
    for i in range(b):
        A = _counting_rank_step(A, i)
    return A


def radix_sort_blocked(A, b: int = 32, r: int = 8):
    """Generalized b/r passes of r bits (book Sec 5.2). Uses multiprefix-equivalent counting."""
    A = list(A)
    for shift in range(0, b, r):
        mask = (1 << r) - 1
        cnt = [0] * (1 << r)
        for a in A:
            cnt[(a >> shift) & mask] += 1
        # exclusive scan of counts
        pos = [0] * (1 << r)
        s = 0
        for k in range(1 << r):
            pos[k] = s
            s += cnt[k]
        B = [0] * len(A)
        nxt = pos[:]
        for a in A:
            k = (a >> shift) & mask
            B[nxt[k]] = a
            nxt[k] += 1
        A = B
    return A


def quicksort_cost(n):  # expected
    return Cost(work=n * math.log2(max(2, n)), depth=math.log2(max(2, n)) ** 2, name="quicksort")


def radix_cost(n, b=32):
    return Cost(work=b * n, depth=b * math.log2(max(2, n)), name="radix")
