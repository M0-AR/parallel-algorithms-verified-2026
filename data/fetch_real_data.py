"""Real-data loaders: public graphs + live market data (no API key).

- SNAP-style graphs: tries Stanford SNAP small graphs (email-Eu-core, etc.);
  falls back to networkx generators with fixed seeds if offline.
- Live market data: Stooq free daily CSV (no key). Falls back to geometric
  random walk with fixed seed if offline. Used to verify sorting/scan on
  real price series (sort closes, scan cumulative returns, dedup tick symbols).

All fallbacks are seeded => bitwise-reproducible. Every experiment logs
`provenance: {source: live|cache|synthetic, url, sha, n}`.
"""
from __future__ import annotations
import hashlib
import io
import os
import random
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(__file__))


def _fetch(url: str, timeout: int = 15) -> bytes | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def load_graph_real(n_target: int = 2000, seed: int = 0):
    """Try SNAP email-Eu-core edges; else Barabasi-Albert synthetic. Returns (n, edge_list)."""
    urls = [
        "https://snap.stanford.edu/data/email-Eu-core.txt.gz",
        "https://snap.stanford.edu/data/email-Eu-core.txt",
    ]
    for u in urls:
        raw = _fetch(u)
        if raw:
            try:
                import gzip
                if u.endswith(".gz"):
                    raw = gzip.decompress(raw)
                edges, nodes = [], set()
                for line in raw.decode("utf-8", "ignore").splitlines():
                    if line.startswith("#") or not line.strip():
                        continue
                    a = line.split()
                    if len(a) >= 2:
                        edges.append((int(a[0]), int(a[1])))
                        nodes.update((int(a[0]), int(a[1])))
                    if len(edges) >= n_target * 4:
                        break
                # compact ids
                vals = sorted(nodes)
                comp = {v: i for i, v in enumerate(vals)}
                E = [(comp[a], comp[b]) for (a, b) in edges if a in comp and b in comp]
                # undirected both directions (book convention)
                E2 = E + [(b, a) for (a, b) in E]
                n = len(vals)
                prov = {"source": "live", "url": u, "sha": hashlib.sha256(raw[:100000]).hexdigest()[:16], "n": n, "m": len(E2)}
                return n, E2, prov
            except Exception:
                continue
    # synthetic fallback (seeded)
    import networkx as nx
    g = nx.barabasi_albert_graph(max(10, n_target // 4), 3, seed=seed)
    n = g.number_of_nodes()
    E = [(u, v) for (u, v) in g.edges()] + [(v, u) for (u, v) in g.edges()]
    return n, E, {"source": "synthetic", "url": "networkx:barabasi_albert", "sha": f"seed{seed}", "n": n, "m": len(E)}


def load_market_closes(symbol: str = "aapl.us", n_fallback: int = 5000, seed: int = 0):
    """Live market closes: Yahoo chart API (no key) -> Stooq -> seeded GBM fallback."""
    import json as _json
    # 1) Yahoo (verified live 2026-10-01)
    try:
        req = urllib.request.Request(
            "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d&range=5y",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        j = _json.loads(raw)
        closes = j["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c]
        if len(closes) > 100:
            prov = {"source": "live", "url": "yahoo:AAPL_5y_1d", "sha": hashlib.sha256(raw[:50000]).hexdigest()[:16], "n": len(closes)}
            return [float(c) for c in closes], prov
    except Exception:
        pass
    # 2) Stooq daily CSV (no key)
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    raw = _fetch(url)
    if raw and len(raw) > 200 and b"Close" in raw[:500]:
        try:
            lines = raw.decode("utf-8", "ignore").splitlines()
            closes = [float(l.split(",")[4]) for l in lines[1:] if len(l.split(",")) > 4]
            closes = [c for c in closes if c > 0]
            if len(closes) > 100:
                prov = {"source": "live", "url": url, "sha": hashlib.sha256(raw[:50000]).hexdigest()[:16], "n": len(closes)}
                return closes, prov
        except Exception:
            pass
    rng = random.Random(seed)
    price, out = 100.0, []
    for _ in range(n_fallback):
        price *= 1 + rng.gauss(0.0005, 0.015)
        out.append(price)
    return out, {"source": "synthetic", "url": "gbm:seed0", "sha": f"seed{seed}", "n": len(out)}
