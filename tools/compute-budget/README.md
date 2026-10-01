# tools/compute-budget

Spike S2: can the classical pipeline (MinHash/LSH, incremental on change) run entirely inside Forge? Write-up:
[`docs/spikes/02-forge-only-compute-feasibility.md`](../../docs/spikes/02-forge-only-compute-feasibility.md).

```
node --expose-gc tools/compute-budget/bench/minhash-bench.mjs --out tools/compute-budget/bench/results.json   # re-measure (Node >= 20)
python tools/compute-budget/run.py            # print every table
python tools/compute-budget/run.py --write    # regenerate BUDGET.md
python tools/compute-budget/run.py --check    # exit 1 if BUDGET.md is stale (CI does this)
python -m unittest discover -s tools/compute-budget/tests -v
```

| File | Role |
|---|---|
| `bench/minhash-bench.mjs` | Times the per-page fingerprint pipeline and the memory of in-memory LSH indexes. **MEASURED on whatever machine runs it**, not on Forge |
| `bench/results.json` | The committed measurement, with the machine recorded in `meta` |
| `limits.json` | Every Atlassian limit and price, each with an **evidence grade and a source URL** |
| `budget.py` | Pure functions: storage, CPU, REST quota, fan-out, cost, and the pre-registered criteria G1 to G6 |
| `report.py`, `run.py` | Render `BUDGET.md` (generated; do not edit) |

## Evidence

Only `manifest_schema` in `limits.json` is `VERIFIED` (read from the `@forge/manifest` npm package). Everything else is
`ASSUMED (search-reported)`, because the environment that produced it could not fetch `*.atlassian.com`. After confirming a limit
from its source URL, change its `evidence`, then run `python tools/compute-budget/run.py --write` and commit the new `BUDGET.md`.
Two tests pin that *only* the manifest schema is graded `VERIFIED` and that the pre-registered parameters have not drifted, so
changing either is a deliberate edit.

## Re-measuring on Forge hardware

The sandbox CPU is not Forge's. To get a real figure, paste `fingerprint()` and its helpers into a throwaway Forge function,
time 1,000 synthetic pages with `performance.now()`, and compare with the sandbox's weighted figure in `BUDGET.md` section 1;
set `core_ratio` in `budget.py` accordingly.
