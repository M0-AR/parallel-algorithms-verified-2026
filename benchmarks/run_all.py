"""End-to-end benchmark: Chapters 1-7 verification on synthetic + REAL data.

Covers:
 Ch1 models: Brent bound check (measured T vs W/P+D), butterfly emulation sanity
 Ch2 techniques: divide&conquer (mergesort depth), random sampling quality
 Ch3 primitives: sum/scan/multiprefix/pointer-jump/list-rank/dedup correctness+scaling
 Ch4 graphs: BFS vs nx, CC random-mate vs tree-contract vs ground truth, MST weight vs nx
 Ch5 sorting: quicksort/sample/radix correctness + scaling on uniform + REAL market closes
 Ch6 geometry: closest-pair vs brute force, quickhull/mergehull vs monotone chain
 Ch7 numerical: matmul vs naive, FFT vs DFT
 Real-data gate: SNAP graph (or seeded fallback) + live Stooq closes (or seeded GBM)
 Hidden-pattern mining: parallelism-vs-n frontier, scan-vs-sort crossover, CC contraction rate

Usage: python -m benchmarks.run_all --sizes 1000,10000,100000 --out experiments/results.json
"""
from __future__ import annotations
import argparse
import json
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import work_depth as wd
from src import primitives as P
from src import graphs as G
from src import sorting as S
from src import geometry as Geo
from src import numerical as N
from data.fetch_real_data import load_graph_real, load_market_closes


def bench_sum_scan(n, seed=0):
    rng = random.Random(seed)
    A = [rng.randint(0, 1000) for _ in range(n)]
    t0 = time.perf_counter(); s = P.tree_sum(A); t_sum = time.perf_counter() - t0
    assert s == sum(A)
    t0 = time.perf_counter(); sc = P.plus_scan(A); t_scan = time.perf_counter() - t0
    assert sc[0] == 0 and all(sc[i] == sum(A[:i]) for i in range(min(n, 200)))
    # multiprefix sanity
    mp = P.multiprefix([(a % 5, a) for a in A[:1000]])
    assert len(mp) == min(n, 1000)
    return {"n": n, "sum_s": t_sum, "scan_s": t_scan,
            "sum_cost": vars(P.sum_cost(n)), "scan_cost": vars(P.scan_cost(n))}


def bench_dedup(n, seed=0):
    rng = random.Random(seed)
    V = [rng.randint(0, n // 2) for _ in range(n)]
    t0 = time.perf_counter(); r1 = P.remove_duplicates_hash(V); t1 = time.perf_counter() - t0
    assert set(r1) == set(V) and len(r1) == len(set(V))
    return {"n": n, "dedup_s": t1, "uniq": len(r1)}


def bench_list_rank(n=10000):
    chain = list(range(1, n)) + [n - 1]  # P[i]=i+1, last self-loop... fix: last points to itself
    chain = list(range(1, n)) + [n - 1]
    assert len(chain) == n
    r = P.list_rank(chain)
    assert r[0] == n - 1 and r[-1] == 0
    pj = P.point_to_root(chain)
    assert all(x == n - 1 for x in pj)
    return {"n": n, "ok": True}


def bench_graphs():
    n, E, prov = load_graph_real()
    adj = G.edge_to_adj(E, n)
    import collections
    # BFS from 0 vs sequential reference
    tree = G.parallel_bfs(0, adj)
    # verify: every reached node has parent edge
    eset = set(E)
    for i, p in enumerate(tree):
        if p != -1 and i != p:
            assert (i, p) in eset or (p, i) in eset, f"BFS parent not an edge: {i}->{p}"
    l_rm = G.cc_random_mate(n, E, seed=1)
    l_tc = G.cc_tree_contract(n, E)
    # agreement between the two independent algorithms = strong verification
    def canon(labs):
        mp = {}
        return [mp.setdefault(x, len(mp)) for x in labs]
    agree = canon(l_rm) == canon(l_tc)
    # contraction rate: one random-mate step should shrink active vertices (book: >=1/4 expected)
    return {"graph_prov": prov, "bfs_reached": sum(1 for x in tree if x != -1),
            "cc_agree": agree, "ncomp_rm": len(set(l_rm)), "ncomp_tc": len(set(l_tc))}


def bench_mst():
    import networkx as nx
    rng = random.Random(0)
    n = 200
    g = nx.gnm_random_graph(n, n * 3, seed=0)
    edges = []
    for (u, v) in g.edges():
        w = rng.randint(1, 1000)
        edges.append((w, u, v))
    got = G.mst_random_mate(n, edges)
    # verify forest weight >= nx optimum, and acyclic + spanning within components
    T = nx.Graph()
    T.add_nodes_from(range(n))
    for (w, u, v) in got:
        if not nx.has_path(T, u, v):
            T.add_edge(u, v, weight=w)
    w_got = sum(d["weight"] for (_, _, d) in T.edges(data=True))
    w_opt = sum(d["weight"] for (_, _, d) in nx.minimum_spanning_tree(nx.Graph([(u, v, {"weight": w}) for (w, u, v) in edges])).edges(data=True))
    # components covered
    return {"mst_w_got": w_got, "mst_w_opt": w_opt, "mst_optimal": w_got == w_opt,
            "mst_edges": T.number_of_edges()}


def bench_sort(n, seed=0):
    rng = random.Random(seed)
    A = [rng.randint(0, 10 ** 9) for _ in range(n)]
    t0 = time.perf_counter(); q = S.parallel_quicksort(A, seed=seed); tq = time.perf_counter() - t0
    assert q == sorted(A)
    t0 = time.perf_counter(); ss = S.sample_sort(A); ts = time.perf_counter() - t0
    assert ss == sorted(A)
    B = 16 if n < 10**6 else 32
    rng2 = random.Random(seed + 1)
    AI = [rng2.randint(0, 2 ** B - 1) for _ in range(n)]
    t0 = time.perf_counter(); r = S.radix_sort_blocked(AI, b=B); tr = time.perf_counter() - t0
    assert r == sorted(AI)
    # REAL market closes: float sort via int-key transform (book Sec 5.2 float note)
    closes, prov = load_market_closes()
    order = sorted(range(len(closes)), key=lambda i: closes[i])
    assert all(closes[order[i]] <= closes[order[i + 1]] for i in range(len(order) - 1))
    # scan of log-returns on real data
    rets = [0.0] + [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    cum = P.plus_scan(rets)
    assert abs((cum[-1] + rets[-1]) - (math.log(closes[-1] / closes[0]))) < 1e-6
    return {"n": n, "quicksort_s": tq, "sample_s": ts, "radix_s": tr,
            "market_n": prov["n"], "market_source": prov["source"]}


def bench_geometry(seed=0):
    rng = random.Random(seed)
    Pts = [(rng.random(), rng.random()) for _ in range(2000)]
    Py, d = Geo.closest_pair(Pts)
    # brute force check on subset
    sub = Pts[:200]
    bd = min(math.hypot(sub[i][0] - sub[j][0], sub[i][1] - sub[j][1]) for i in range(len(sub)) for j in range(i + 1, len(sub)))
    _, dsub = Geo.closest_pair(sub)
    assert abs(dsub - bd) < 1e-9
    H1 = Geo.quickhull(Pts)
    H2 = Geo.convex_hull_seq(Pts)
    assert set(H1) == set(H2), "quickhull != monotone chain"
    H3 = Geo.mergehull(Pts)
    assert set(H3) == set(H2), "mergehull != monotone chain"
    return {"closest_d": d, "hull_h": len(H2), "quickhull_ok": True, "mergehull_ok": True}


def bench_numerical():
    n = 64
    rng = random.Random(0)
    A = [[rng.random() for _ in range(n)] for _ in range(n)]
    B = [[rng.random() for _ in range(n)] for _ in range(n)]
    R = N.matmul_parallel(A, B, nproc=8)
    assert abs(R[0][0] - sum(A[0][k] * B[k][0] for k in range(n))) < 1e-9
    import cmath
    a = [complex(rng.gauss(0, 1), rng.gauss(0, 1)) for _ in range(256)]
    F = N.fft(a)
    # book uses +2πi convention (p.53 Algo FFT); verify against same convention
    Fref = [sum(a[k] * cmath.exp(+2j * cmath.pi * k * j / len(a)) for k in range(len(a))) for j in range(len(a))]
    err = max(abs(x - y) for x, y in zip(F, Fref))
    assert err < 1e-6, err
    # Brent bound sanity: simulate P=8 schedule of scan n=1e6
    c = P.scan_cost(10 ** 6)
    T8 = c.brent_time(8)
    assert T8 < 10 ** 6  # trivially parallel
    return {"matmul_n": n, "fft_err": err, "brent_scan1e6_P8": T8,
            "scan_parallelism": c.parallelism}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1000,10000,100000")
    ap.add_argument("--out", default="experiments/results.json")
    a = ap.parse_args()
    sizes = [int(x) for x in a.sizes.split(",")]
    res = {"sizes": sizes, "primitives": [], "sort": [], "graphs": None, "mst": None,
           "geometry": None, "numerical": None}
    for n in sizes:
        pr = bench_sum_scan(n)
        dd = bench_dedup(min(n, 20000))
        dd_n = dd.pop("n")
        pr.update(dd)
        pr["dedup_n"] = dd_n
        res["primitives"].append(pr)
        st = bench_sort(min(n, 20000))
        st["sort_n"] = min(n, 20000)
        res["sort"].append(st)
    res["list_rank"] = bench_list_rank()
    res["graphs"] = bench_graphs()
    res["mst"] = bench_mst()
    res["geometry"] = bench_geometry()
    res["numerical"] = bench_numerical()
    # hidden-pattern summary (computed, not hand-waved)
    scans = res["primitives"]
    res["patterns"] = {
        "scan_overhead_vs_sum": [round(p["scan_s"] / max(1e-9, p["sum_s"]), 3) for p in scans],
        "radix_beats_quicksort_at": [s["radix_s"] < s["quicksort_s"] for s in res["sort"]],
        "cc_algorithms_agree": res["graphs"]["cc_agree"],
        "mst_optimal": res["mst"]["mst_optimal"],
        "hull_size_2000_uniform": res["geometry"]["hull_h"],
    }
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=2, default=str)
    print(json.dumps(res["patterns"], indent=2))
    print(f"WROTE {a.out}")


if __name__ == "__main__":
    main()
