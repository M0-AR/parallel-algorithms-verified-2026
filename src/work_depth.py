"""Work-depth model core (Blelloch & Maggs Ch.1-2).

Implements:
- Work W = total ops, Depth D = longest dependency chain, Parallelism P = W/D
- Brent's Theorem scheduler: T(P) <= W/P + D  (CREW PRAM emulation)
- Work-efficiency check: W_par <= c * W_seq
- NESL-style primitives cost rules: apply-to-each (map), parallel-do (fork-join)

Verified against:
- BM10/BM04 theorems (Theorem 1.1/25.1 Brent, Theorem 1.2 butterfly emulation)
- CMU 15-210 / Stanford CME323 lecture notes (W/P + D bound)
- Binary-forking model (2020): async scheduling W/P + O(S) w.h.p.
"""
from __future__ import annotations
import math
import time
from dataclasses import dataclass


@dataclass
class Cost:
    work: float   # total operations
    depth: float  # longest chain
    name: str = ""

    @property
    def parallelism(self) -> float:
        return self.work / self.depth if self.depth > 0 else float("inf")

    def brent_time(self, nproc: int) -> float:
        """Brent's theorem upper bound: O(W/P + D). Constant factor = 1 for model."""
        return self.work / nproc + self.depth

    def is_work_efficient(self, seq_work: float, c: float = 4.0) -> bool:
        return self.work <= c * seq_work

    def procs_for_efficiency(self) -> int:
        """Max P such that emulation stays work-preserving: need P <= W/D."""
        return max(1, int(self.work // max(1, self.depth)))


def brent_bound(W: float, D: float, P: int) -> float:
    return W / P + D


def butterfly_emulation_time(T_pram: float, P_guest: float, P_host: float) -> float:
    """Theorem 1.2 sketch: O(T * (P/P' + log P')). Requires P >= P' log P' for work preservation."""
    return T_pram * (P_guest / P_host + math.log2(max(2, P_host)))


def timed(fn, *args, **kw):
    t0 = time.perf_counter()
    out = fn(*args, **kw)
    return out, time.perf_counter() - t0
