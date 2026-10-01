# tools/cost-model

Spike S1: what does the LLM verdict stage cost per tenant, and is that a problem? Write-up:
[`docs/spikes/01-forge-llm-cost-model.md`](../../docs/spikes/01-forge-llm-cost-model.md). Python 3.10+, standard library only.

```
python tools/cost-model/run.py            # print every sensitivity table
python tools/cost-model/run.py --write    # regenerate SENSITIVITY.md
python tools/cost-model/run.py --check    # exit 1 if SENSITIVITY.md is stale (CI does this)
python -m unittest discover -s tools/cost-model/tests -v
```

| File | Role |
|---|---|
| `prices.json` | Every price, limit and rate, each with an **evidence grade and a source URL** |
| `cost_model.py` | Pure functions over a frozen `Scenario`: cost, revenue, margin, break-even, throughput |
| `report.py` | The pre-registered base case and criteria K1–K4; renders the tables |
| `SENSITIVITY.md` | Generated output. Do not edit by hand |

## Parameters

Pages, funnel yield (candidate pairs per page), tokens per verdict call, model price, monthly churn, calls per pair, users,
price per user, and the Atlassian take rate. `pair_multiplier` covers the reading of "yield" in which each flagged page brings
several partners.

## Evidence

Every Atlassian figure in `prices.json` is `ASSUMED (search-reported)`: the environment that produced it could not fetch
`*.atlassian.com`. After confirming a figure from its source URL, change its `evidence` to `VERIFIED` (add the date), then run
`python tools/cost-model/run.py --write` and commit the regenerated `SENSITIVITY.md`. The base case and the criteria are pinned by
tests, so changing one is a deliberate edit, not an accident.

## Not modelled

Forge storage (KVS or SQL), the classical pipeline's own compute (Spike S2), payment fees and support. Forge's free allowance is
ignored, which is conservative per tenant.
