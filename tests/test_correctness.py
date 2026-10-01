"""Correctness tests — every theorem/algorithm cross-checked, no hand-waving."""
import math
import random


def test_sum_scan():
    from src.primitives import tree_sum, plus_scan, multiprefix
    assert tree_sum([]) == 0
    assert tree_sum([5]) == 5
    assert tree_sum([1, 2, 3, 4]) == 10
    assert tree_sum([1, 2, 3]) == 6
    assert plus_scan([3, 5, 3, 1, 6]) == [0, 3, 8, 11, 12]
    mp = multiprefix([(1, 5), (0, 2), (0, 3), (1, 4), (0, 1), (2, 2)])
    assert mp == [0, 0, 2, 5, 5, 0]


def test_pointer_listrank():
    from src.primitives import point_to_root, list_rank
    assert point_to_root([4, 1, 6, 4, 1, 6, 3]) == [1, 1, 1, 1, 1, 1, 1]
    assert list_rank([1, 2, 3, 3]) == [3, 2, 1, 0]


def test_dedup():
    from src.primitives import rem_duplicates_flags, remove_duplicates_hash
    assert sorted(rem_duplicates_flags([3, 1, 3, 2, 1])) == [1, 2, 3]
    rng = random.Random(0)
    V = [rng.randint(0, 50) for _ in range(500)]
    assert set(remove_duplicates_hash(V)) == set(V)


def test_bfs_cc():
    from src.graphs import parallel_bfs, cc_random_mate, cc_tree_contract, edge_to_adj
    adj = [[1, 2], [0, 3], [0, 3], [1, 2, 4], [3]]
    E = [(u, v) for v, ns in enumerate(adj) for u in ns]
    t = parallel_bfs(0, adj)
    assert t[0] == 0 and all(x != -1 for x in t)
    l1, l2 = cc_random_mate(5, E, seed=0), cc_tree_contract(5, E)
    assert len(set(l1)) == 1 and len(set(l2)) == 1
    # disconnected
    E2 = [(0, 1), (1, 0)]
    assert len(set(cc_tree_contract(3, E2))) == 2


def test_sort():
    from src.sorting import parallel_quicksort, sample_sort, radix_sort_blocked
    rng = random.Random(1)
    A = [rng.randint(0, 100) for _ in range(1000)]
    assert parallel_quicksort(A, seed=1) == sorted(A)
    assert sample_sort(A) == sorted(A)
    assert radix_sort_blocked(A, b=16) == sorted(A)


def test_geometry():
    from src.geometry import closest_pair, quickhull, convex_hull_seq, mergehull
    Pts = [(0, 0), (1, 0), (0, 1), (1, 1), (0.5, 0.5)]
    _, d = closest_pair(Pts)
    assert abs(d - math.sqrt(0.5)) < 1e-9
    assert set(quickhull(Pts)) == set(convex_hull_seq(Pts))
    assert set(mergehull(Pts)) == set(convex_hull_seq(Pts))


def test_numerical():
    from src.numerical import matmul_parallel, fft
    import cmath
    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]
    assert matmul_parallel(A, B) == [[19, 22], [43, 50]]
    a = [1, 1, 1, 1, 0, 0, 0, 0]
    F = fft(a)
    # book convention: +2πi (forward with positive exponent); match implementation
    ref = [sum(a[k] * cmath.exp(+2j * cmath.pi * k * j / 8) for k in range(8)) for j in range(8)]
    assert max(abs(x - y) for x, y in zip(F, ref)) < 1e-9


def test_brent():
    from src.work_depth import Cost, butterfly_emulation_time
    c = Cost(work=10**6, depth=100, name="t")
    assert c.parallelism == 10**4
    assert c.brent_time(8) == 10**6 / 8 + 100
    assert butterfly_emulation_time(10, 1024, 64) > 10
