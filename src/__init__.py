"""Parallel Algorithms — Blelloch & Maggs verified benchmark."""
from .work_depth import Cost, brent_bound, butterfly_emulation_time
from . import primitives, graphs, sorting, geometry, numerical

__all__ = ["Cost", "brent_bound", "butterfly_emulation_time",
           "primitives", "graphs", "sorting", "geometry", "numerical"]
__version__ = "1.0.0"
