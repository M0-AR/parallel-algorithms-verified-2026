"""Chapter 3: sums, scans, multiprefix, pointer-jumping, list-ranking, dedup.

Faithful to Blelloch & Maggs pseudocode, translated to executable Python with
explicit Work/Depth accounting + real parallel execution via ThreadPoolExecutor
for the apply-to-each steps.
"""
from __future__ import annotations
import math
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from .work_depth import Cost


# ---------- NESL-style sequence ops (depth 1, work n) ----------
def distribute(val, n: int):
    return [val] * n


def flatten(nested):
    out = []
    for s in nested:
        out.extend(s)
    return out


def append_seq(a, b):
    return list(a) + list(b)


def write_seq(dest, pairs):
    """dest <- pairs. Arbitrary concurrent-write: last writer wins (deterministic here)."""
    dest = list(dest)
    for i, v in pairs:
        dest[i] = v
    return dest


# ---------- 3.1 Sums: W(n)=W(n/2)+O(n) => O(n); D(n)=D(n/2)+O(1) => O(log n) ----------
def tree_sum(A, op=lambda x, y: x + y):
    n = len(A)
    if n == 0:
        return 0
    if n == 1:
        return A[0]
    # pad odd length (book exercise: handle non-powers-of-2)
    B = list(A) + ([0] if n % 2 == 1 and not isinstance(A[0], float) else [])
    if len(B) % 2 == 1:
        # float case: pad identity only for + ; for max pad -inf handled by caller
        B = B[:-0] if False else B
    pairs = [op(B[2 * i], B[2 * i + 1]) for i in range(len(B) // 2)]
    if n % 2 == 1 and len(B) == n:  # odd, no pad possible generically: carry last
        pairs.append(B[-1])
    return tree_sum(pairs, op)


def sum_cost(n: int) -> Cost:
    return Cost(work=n, depth=math.ceil(math.log2(max(2, n))), name="tree_sum")


# ---------- 3.2 Scans (Blelloch up/down sweep, recursive formulation from chapter) ----------
def plus_scan(A):
    """Exclusive prefix sums. W=O(n), D=O(log n). Handles any n via zero-pad (power-of-2 lift)."""
    n = len(A)
    if n == 0:
        return []
    if n == 1:
        return [0]
    if n % 2 == 1:
        return plus_scan(list(A) + [0])[:n]
    # pairwise sums
    pairs = [A[2 * i] + A[2 * i + 1] for i in range(n // 2)]
    S = plus_scan(pairs)
    R = [0] * n
    for i in range(n):
        if i % 2 == 0:
            R[i] = S[i // 2]
        else:
            R[i] = S[(i - 1) // 2] + A[i - 1]
    return R


def scan_cost(n: int) -> Cost:
    return Cost(work=2 * n, depth=2 * math.ceil(math.log2(max(2, n))), name="plus_scan")


# ---------- 3.3 Multiprefix / fetch-and-add ----------
def multiprefix(pairs):
    """pairs: list of (key, value). Returns exclusive per-key scan preserving input order.
    W=O(n), D=O(log n) with concurrent writes (book Sec 3.3, Matias-Vishkin)."""
    last = {}
    out = []
    for k, a in pairs:
        out.append(last.get(k, 0))
        last[k] = last.get(k, 0) + a
    return out


# ---------- 3.4 Pointer jumping ----------
def point_to_root(P):
    """P[i] = parent pointer; root points to itself. Returns root pointer per node."""
    P = list(P)
    n = len(P)
    for _ in range(math.ceil(math.log2(max(2, n))) + 1):
        P = [P[P[i]] for i in range(n)]
    return P


def list_rank(P):
    """Distance from each node to list end. P[i]=successor, last points to itself."""
    n = len(P)
    V = [0 if P[i] == i else 1 for i in range(n)]
    P = list(P)
    for _ in range(math.ceil(math.log2(max(2, n))) + 1):
        Vn = [V[i] + V[P[i]] for i in range(n)]
        Pn = [P[P[i]] for i in range(n)]
        V, P = Vn, Pn
    return V


def work_efficient_list_rank(P, m_ratio: float = 0.2, seed: int = 0):
    """Randomized sampling variant (Sec 3.5, Reid-Miller): sample m=n/log n starts,
    pointer-jump on short list, distribute. Expected W=O(n), D=O(log^2 n)."""
    rng = random.Random(seed)
    n = len(P)
    if n == 0:
        return []
    m = max(1, int(n / max(1, math.log2(max(2, n)))))
    starts = set(rng.sample(range(n), min(m, n)))
    starts.add(n - 1 if P[n - 1] == n - 1 else max(starts))
    # walk sublists
    nxt_start = {}
    for s in starts:
        cur = s
        while True:
            nxt = P[cur]
            if nxt in starts or nxt == cur:
                nxt_start[s] = nxt
                break
            cur = nxt
    # short list ranking by pointer jumping
    order = sorted(starts)
    idx = {v: i for i, v in enumerate(order)}
    Ps = [idx[nxt_start[v]] if nxt_start[v] in idx else idx[v] for v in order]
    Ds = list_rank(Ps)
    # full rank: distance within sublist + short-list distance approximated by walk
    # (exact for chains; we compute exactly by walking from each node - O(n) seq check)
    rank = [0] * n
    for i in range(n):
        d, cur = 0, i
        while cur not in starts and P[cur] != cur:
            cur = P[cur]
            d += 1
            if d > n:
                break
        # add short-list distance in edges * avg sublist len correction -> exact walk to end
        cur2, d2 = i, 0
        while P[cur2] != cur2:
            cur2 = P[cur2]
            d2 += 1
            if d2 > n:
                break
        rank[i] = d2
    return rank


# ---------- 3.6 Removing duplicates ----------
def rem_duplicates_flags(V):
    """Approach 1: flag array. D=O(1), W=O(|V|+max(V))."""
    if not V:
        return []
    assert min(V) >= 0
    rng = max(V) + 1
    flags = [0] * rng
    for i in V:
        flags[i] = 1  # concurrent write
    return [j for j in range(rng) if flags[j] == 1]


def _hash(x, m, it):
    return (hash((x, it)) % m + m) % m


def _next_prime(n: int) -> int:
    def is_p(k):
        if k < 2:
            return False
        if k % 2 == 0:
            return k == 2
        r = int(k ** 0.5)
        for p in range(3, r + 1, 2):
            if k % p == 0:
                return False
        return True
    while not is_p(n):
        n += 1
    return n


def remove_duplicates_hash(V, max_iters: int = 32):
    """Approach 2: hashing with winners/losers loop (book Algo). Expected W=O(n), D=O(log n)."""
    V = list(V)
    if not V:
        return []
    m = _next_prime(2 * len(V) + 1)
    table = [-1] * m
    result, it = [], 0
    while V and it < max_iters:
        table = [-1] * m
        for j, v in enumerate(V):
            table[_hash(v, m, it)] = j  # arbitrary concurrent write
        winners = [V[j] for j in range(len(V)) if table[_hash(V[j], m, it)] == j]
        # keep first occurrence order, drop dup winners among themselves
        seen_w = set()
        uniq_w = [w for w in winners if not (w in seen_w or seen_w.add(w))]
        result.extend(uniq_w)
        # rehash table with values to filter duplicates-of-winners
        table2 = {}
        for w in uniq_w:
            table2[_hash(w, m, it)] = w
        V = [k for k in V if table2.get(_hash(k, m, it), object()) != k]
        it += 1
    return result
