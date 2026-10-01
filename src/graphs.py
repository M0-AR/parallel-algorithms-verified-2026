"""Chapter 4: graphs — BFS, connected components (random-mate + tree-contract), MST."""
from __future__ import annotations
import math
import random
from .primitives import remove_duplicates_hash
from .work_depth import Cost


def adj_to_edge(adj):
    E = []
    for v, nbrs in enumerate(adj):
        for u in nbrs:
            E.append((v, u))
    return E


def edge_to_adj(E, n):
    adj = [[] for _ in range(n)]
    for u, v in E:
        adj[u].append(v)
    return adj


def bfs_cost(n, m, D):
    return Cost(work=n + m, depth=D, name="bfs")


def parallel_bfs(source, adj):
    """Book Algo BFS(s,G): frontier expansion + arbitrary concurrent-write parent claim."""
    n = len(adj)
    tree = [-1] * n
    tree[source] = source
    front = [source]
    while front:
        E = [(u, v) for v in front for u in adj[v]]
        E2 = [(u, v) for (u, v) in E if tree[u] == -1]
        for (u, v) in E2:  # concurrent write: first claim wins (arbitrary -> deterministic here)
            if tree[u] == -1:
                tree[u] = v
        front = [u for (u, v) in E2 if tree[u] == v]
    return tree


def cc_random_mate(n, E, seed=0):
    """Recursive random-mate contraction (book Algo). Returns labels: same iff connected."""
    rng = random.Random(seed)
    labels = list(range(n))
    cur_seed = [seed]

    def rec(labels, E):
        if not E:
            return labels
        # filter self-loops already removed by caller; active vertices = endpoints
        active = sorted({u for e in E for u in e})
        amap = {v: i for i, v in enumerate(active)}
        child = {v: rng.randint(0, 1) for v in active}
        hooks = [(u, v) for (u, v) in E if child.get(u, 0) == 1 and child.get(v, 1) == 0]
        for (u, v) in hooks:
            labels[u] = labels[v]
        E2 = []
        for (u, v) in E:
            lu, lv = labels[u], labels[v]
            if lu != lv:
                E2.append((lu, lv))
        # relabel to compact ids to keep recursion finite (map labels to 0..k)
        vals = sorted(set(labels))
        comp = {v: i for i, v in enumerate(vals)}
        labels_c = [comp[x] for x in labels]
        E_c = [(comp[u], comp[v]) for (u, v) in E2]
        # remove duplicate edges to bound blowup (book Sec 4.3.3 note)
        E_c = list({e for e in E_c})
        out = rec(labels_c, E_c)
        # expand: children take root's final label
        final = [out[comp[labels[i]]] if False else None for i in range(n)]
        # simpler: map current labels through out
        res = [out[comp[labels[i]]] for i in range(n)]
        # hooks expansion: u gets v's final label
        for (u, v) in hooks:
            res[u] = res[v] if res[v] == res[v] else res[u]
        return res

    # iterative version to avoid deep recursion issues: use loop with same logic
    labels = list(range(n))
    Ecur = [(u, v) for (u, v) in E if u != v]
    steps = 0
    hook_stack = []
    # contract down
    while Ecur and steps < 64:
        active = sorted({u for e in Ecur for u in e})
        child = {v: rng.randint(0, 1) for v in active}
        hooks = [(u, v) for (u, v) in Ecur if child.get(u) == 1 and child.get(v) == 0]
        hook_stack.append(hooks)
        for (u, v) in hooks:
            labels[u] = labels[v]
        Ecur = [(labels[u], labels[v]) for (u, v) in Ecur if labels[u] != labels[v]]
        Ecur = list({e for e in Ecur})
        steps += 1
    # expand back: propagate final root labels to children (labels already point to parents)
    # path-compress
    for _ in range(int(math.log2(max(2, n))) + 2):
        labels = [labels[labels[i]] for i in range(n)]
    return labels


def cc_tree_contract(n, E):
    """Deterministic conditional-hook (larger->smaller) + pointer jumping, bidirectional pick."""
    labels = list(range(n))
    Ecur = [(u, v) for (u, v) in E if u != v]
    steps = 0
    while Ecur and steps < 64:
        hooks_lo = [(u, v) for (u, v) in Ecur if u > v]
        hooks_hi = [(u, v) for (u, v) in Ecur if u < v]
        # Lemma 4.1: pick direction hooking more vertices
        cu = {u for (u, v) in hooks_lo}
        cl = {u for (u, v) in hooks_hi}
        hooks = hooks_lo if len(cu) >= len(cl) else hooks_hi
        for (u, v) in hooks:
            labels[u] = min(labels[u], labels[v])
        # pointer jumping to roots
        for _ in range(int(math.log2(max(2, n))) + 1):
            labels = [labels[labels[i]] for i in range(n)]
        Ecur = [(labels[u], labels[v]) for (u, v) in Ecur if labels[u] != labels[v]]
        Ecur = list({e for e in Ecur})
        steps += 1
    for _ in range(int(math.log2(max(2, n))) + 1):
        labels = [labels[labels[i]] for i in range(n)]
    return labels


def mst_random_mate(n, edges):
    """edges: list of (w,u,v). Random-mate min-edge hook (book Sec 4.3.4). Returns MST edge set."""
    import random as _r
    rng = _r.Random(0)
    # sort by weight for priority-write emulation
    edges = sorted(edges)
    parent = list(range(n))
    in_mst = []
    Ecur = [(u, v) for (w, u, v) in edges]
    Wcur = {(u, v): w for (w, u, v) in edges}
    Wcur.update({(v, u): w for (w, u, v) in edges})
    steps = 0
    # Boruvka-style with random-mate filter: each step hook children via min edge to a parent
    comp = list(range(n))
    remaining = sorted(edges)
    while remaining and steps < 64:
        comp0 = comp[:]
        comps_active = set(comp0[i] for i in range(n) if any(comp0[u] == comp0[i] or comp0[v] == comp0[i] for (_, u, v) in remaining))
        if len(set(comp0)) <= 1 or not comps_active:
            # check global connectivity of remaining graph
            if len(set(comp0[i] for i in range(n))) <= len(set(comp0)) - 0:
                pass
        # true Boruvka minima: min outgoing edge per component (snapshot comp0)
        min_edge = {}
        for (w, u, v) in remaining:  # sorted => first touch is minimum
            cu, cv = comp0[u], comp0[v]
            if cu == cv:
                continue
            if cu not in min_edge:
                min_edge[cu] = (w, u, v)
            if cv not in min_edge:
                min_edge[cv] = (w, v, u)
        if not min_edge:
            break
        # random-mate filter at component level (book Sec 4.3.4 spirit)
        comp_parent = {c: rng.randint(0, 1) == 0 for c in min_edge}
        filtered = []
        for c, (w, u, v) in min_edge.items():
            if not comp_parent[c] and comp_parent.get(comp0[v], True):
                filtered.append((w, u, v))
        candidates = filtered if filtered else list({e for e in min_edge.values()})
        # union all candidates based on snapshot (Boruvka round)
        for (w, a, b) in candidates:
            in_mst.append((w, a, b))
        # union-find merge
        for (w, a, b) in candidates:
            ra, rb = comp[a], comp[b]
            # re-find with current comp (path already flat-ish); merge rb into ra's set via snapshot roots
            for i in range(n):
                if comp[i] == ra:
                    comp[i] = rb
        remaining = [(w, u, v) for (w, u, v) in remaining if comp[u] != comp[v]]
        steps += 1
    return in_mst
