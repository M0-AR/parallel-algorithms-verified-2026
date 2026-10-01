"""Chapter 7: numerical — parallel matrix multiply, FFT (butterfly)."""
from __future__ import annotations
import math
import cmath
from concurrent.futures import ThreadPoolExecutor
from .primitives import tree_sum
from .work_depth import Cost


def matmul_parallel(A, B, nproc: int = 8):
    l, m, n = len(A), len(B), len(B[0])
    R = [[0] * n for _ in range(l)]

    def row(i):
        for j in range(n):
            R[i][j] = tree_sum([A[i][k] * B[k][j] for k in range(m)])

    with ThreadPoolExecutor(max_workers=nproc) as ex:
        list(ex.map(row, range(l)))
    return R


def matmul_cost(n):
    return Cost(work=n ** 3, depth=math.log2(max(2, n)), name="matmul")


def fft(a):
    """Book Algo FFT (decimation-in-time). W=O(n log n), D=O(log n)."""
    n = len(a)
    if n == 1:
        return list(a)
    with ThreadPoolExecutor(max_workers=2) as ex:
        fe = ex.submit(fft, a[0::2])
        fo = ex.submit(fft, a[1::2])
        even, odd = fe.result(), fo.result()
    out = [0] * n
    for j in range(n // 2):
        w = cmath.exp(2j * cmath.pi * j / n)
        out[j] = even[j] + odd[j] * w
        out[j + n // 2] = even[j] - odd[j] * w
    return out


def fft_cost(n):
    return Cost(work=n * math.log2(max(2, n)), depth=math.log2(max(2, n)) ** 2, name="fft")
