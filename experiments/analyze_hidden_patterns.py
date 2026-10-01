"""Hidden-pattern mining on verified results (no hand-waving: every claim cites results.json)."""
import json, math, os
p = os.path.join(os.path.dirname(__file__), "results.json")
with open(p) as f:
    R = json.load(f)
print("== HIDDEN PATTERNS (verified) ==")
for pr in R["primitives"]:
    W, D = pr["sum_cost"]["work"], pr["sum_cost"]["depth"]
    print(f"n={pr['n']}: sum W={W} D={D} P={W/max(1,D):.1f} t_sum={pr['sum_s']*1e3:.2f}ms t_scan={pr['scan_s']*1e3:.2f}ms scan/sum={pr['scan_s']/max(1e-9,pr['sum_s']):.2f}")
for s in R["sort"]:
    print(f"n={s['n']}: quick={s['quicksort_s']*1e3:.1f}ms sample={s['sample_s']*1e3:.1f}ms radix={s['radix_s']*1e3:.1f}ms market_n={s['market_n']}({s['market_source']})")
print(f"graph: {R['graphs']['graph_prov']} reached={R['graphs']['bfs_reached']} agree={R['graphs']['cc_agree']}")
print(f"mst: got={R['mst']['mst_w_got']} opt={R['mst']['mst_w_opt']} optimal={R['mst']['mst_optimal']}")
print(f"geometry hull_h={R['geometry']['hull_h']} closest_d={R['geometry']['closest_d']:.4f}")
print(f"numerical fft_err={R['numerical']['fft_err']:.2e} brent_P8={R['numerical']['brent_scan1e6_P8']:.1f}")
print("PATTERNS:", json.dumps(R["patterns"], indent=2))
