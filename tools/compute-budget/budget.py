"""Feasibility arithmetic for Spike S2: can the classical pipeline run entirely inside Forge?

Stdlib only; pure functions over a frozen ``Params``. The parameters are the ones fixed in
docs/spikes/02-forge-only-compute-feasibility.md before any number was computed.

Grades: CPU per page comes from ``bench/results.json`` and is MEASURED on the sandbox CPU, not on Forge hardware.
Everything derived from it, and everything built on Atlassian limits (``limits.json``, search-reported), is ESTIMATED.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIMITS_PATH = HERE / "limits.json"
BENCH_PATH = HERE / "bench" / "results.json"

GIB = 1024**3
HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class Params:
    # fingerprint shape
    k: int = 128                       # MinHash permutations, uint32 each
    bands: int = 16                    # LSH bands (rows per band = k / bands)
    # Forge SQL bytes per page (ASSUMED)
    signature_bytes_per_hash: int = 4
    band_row_bytes: int = 70           # one band row, including its index
    meta_bytes: int = 150              # page id, version, content hash, timestamps
    # page-size mix: (words, weight)
    mix: tuple[tuple[int, float], ...] = ((300, 0.60), (1500, 0.30), (6000, 0.09), (20000, 0.01))
    markup: str = "heavy"              # which bench variant to use (28.8 B/word storage format)
    # function
    memory_mb: int = 1024
    mb_per_vcpu: float = 1769.0        # Lambda rule: 1,769 MB is one vCPU (ASSUMED)
    core_ratio: float = 1.0            # sandbox core speed / Lambda vCPU speed (ASSUMED 1.0)
    # REST fetch
    pages_per_request: int = 250
    request_seconds: float = 5.0
    concurrency: int = 10
    # SQL write path
    rows_per_statement: int = 500
    statement_seconds: float = 0.25
    # quota planning shares
    pool_share_best: float = 1.0
    pool_share_plan: float = 0.20
    users: int = 1000
    # steady state
    monthly_edit_rate: float = 0.05
    edit_function_seconds: float = 1.0
    edit_function_gb: float = 0.5
    edit_sql_requests: int = 20
    edit_sql_compute_seconds: float = 1.0
    net_revenue: float = 830.0


def load_limits(path: Path = LIMITS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_bench(path: Path = BENCH_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---- storage (G1) ---------------------------------------------------------------------------------------------


def bytes_per_page(p: Params) -> int:
    return p.k * p.signature_bytes_per_hash + p.bands * p.band_row_bytes + p.meta_bytes


def storage_bytes(p: Params, pages: int) -> int:
    return bytes_per_page(p) * pages


def storage_fraction(p: Params, pages: int, limit_bytes: int = GIB) -> float:
    return storage_bytes(p, pages) / limit_bytes


def max_pages_within(p: Params, fraction: float, limit_bytes: int = GIB) -> int:
    """Largest page count whose index fits in ``fraction`` of the SQL limit."""
    return math.floor(fraction * limit_bytes / bytes_per_page(p))


def rows_per_page(p: Params) -> int:
    return 1 + p.bands  # one page row (with the signature) plus one row per band


# ---- in-memory LSH index (reference for one function holding the whole index) -------------------------------------


def compact_index_bytes(p: Params, pages: int) -> int:
    """Sorted typed arrays: an 8-byte key and a 4-byte id per band entry."""
    return pages * p.bands * 12


# ---- CPU (G2) -------------------------------------------------------------------------------------------------


def mean_words(p: Params) -> float:
    return sum(w * wt for w, wt in p.mix)


def sandbox_us_per_page(p: Params, bench: dict) -> float:
    """Mix-weighted median microseconds per page on the sandbox CPU for the chosen markup variant."""
    by_words = {r["words"]: r["us_per_page_median"] for r in bench["fingerprint"] if r["markup"] == p.markup}
    missing = [w for w, _ in p.mix if w not in by_words]
    if missing:
        raise KeyError(f"bench has no {p.markup!r} result for word sizes {missing}")
    return sum(by_words[w] * wt for w, wt in p.mix)


def cpu_share(memory_mb: float, mb_per_vcpu: float = 1769.0) -> float:
    return min(1.0, memory_mb / mb_per_vcpu)


def forge_us_per_page(p: Params, bench: dict) -> float:
    return sandbox_us_per_page(p, bench) / (cpu_share(p.memory_mb, p.mb_per_vcpu) * p.core_ratio)


def batch_seconds(p: Params, bench: dict, pages: int = 50) -> dict[str, float]:
    """Wall-clock for one batch of ``pages`` in one consumer invocation: fetch + CPU + SQL writes."""
    requests = math.ceil(pages / p.pages_per_request)
    fetch = requests * p.request_seconds
    cpu = pages * forge_us_per_page(p, bench) / 1e6
    statements = math.ceil(pages * rows_per_page(p) / p.rows_per_statement)
    sql = statements * p.statement_seconds
    return {"fetch": fetch, "cpu": cpu, "sql": sql, "total": fetch + cpu + sql}


# ---- REST quota (G3) ------------------------------------------------------------------------------------------


def scan_points(pages: int, pages_per_request: int = 250, base: int = 1, per_object: int = 1) -> int:
    """Points to list-with-bodies every page once: one base point per request plus one per page."""
    return math.ceil(pages / pages_per_request) * base + pages * per_object


def tier2_pool_per_hour(base_points: int, points_per_user: int, users: int) -> int:
    return base_points + points_per_user * users


def scan_hours(points: float, pool_per_hour: float, share: float) -> float:
    return points / (pool_per_hour * share)


def compute_bound_hours(p: Params, bench: dict, pages: int) -> float:
    """Wall-clock if only the consumers limited it: batches of ``pages_per_request`` over ``concurrency`` workers."""
    per = batch_seconds(p, bench, p.pages_per_request)["total"]
    return math.ceil(pages / p.pages_per_request) * per / p.concurrency / 3600


def tenants_onboarded_per_day(pages: int, pool_per_hour: float, share: float, pages_per_request: int = 250) -> float:
    return pool_per_hour * 24 * share / scan_points(pages, pages_per_request)


def steady_points_per_hour(tenants: int, pages: int, edit_rate: float, points_per_edit: float) -> float:
    """Average REST points per hour the incremental path draws from the app-wide pool."""
    return tenants * pages * edit_rate * points_per_edit / HOURS_PER_MONTH


# ---- async fan-out --------------------------------------------------------------------------------------------


def events_needed(pages: int, pages_per_event: int) -> int:
    return math.ceil(pages / pages_per_event)


def push_minutes(events: int, per_minute: int = 500) -> float:
    return events / per_minute


# ---- cost (G4) ------------------------------------------------------------------------------------------------


def function_cost(gb_seconds: float, prices: dict, free: bool = False) -> float:
    billable = max(0.0, gb_seconds - (prices["function_free_gb_seconds_per_month"] if free else 0))
    return billable * prices["function_usd_per_gb_second"]


def sql_cost(storage_gb: float, compute_hours: float, requests: float, prices: dict, free: bool = False) -> dict[str, float]:
    gb_hours = storage_gb * HOURS_PER_MONTH
    if free:
        gb_hours = max(0.0, gb_hours - prices["sql_storage_free_gb_hours_per_month"])
        compute_hours = max(0.0, compute_hours - prices["sql_compute_free_hours_per_month"])
        requests = max(0.0, requests - prices["sql_requests_free_per_month"])
    storage = gb_hours * prices["sql_storage_usd_per_gb_hour"]
    compute = compute_hours * prices["sql_compute_usd_per_hour"]
    reqs = requests / 1e6 * prices["sql_requests_usd_per_million"]
    return {"storage": storage, "compute": compute, "requests": reqs, "total": storage + compute + reqs}


def steady_state_monthly(p: Params, prices: dict, pages: int, free: bool = False) -> dict[str, float]:
    edits = pages * p.monthly_edit_rate
    fn = function_cost(edits * p.edit_function_seconds * p.edit_function_gb, prices, free)
    sql = sql_cost(storage_bytes(p, pages) / GIB, edits * p.edit_sql_compute_seconds / 3600, edits * p.edit_sql_requests, prices, free)
    return {"edits": edits, "functions": fn, "sql_storage": sql["storage"], "sql_compute": sql["compute"],
            "sql_requests": sql["requests"], "total": fn + sql["total"]}


def backfill_one_time(p: Params, bench: dict, prices: dict, pages: int) -> dict[str, float]:
    batches = math.ceil(pages / p.pages_per_request)
    per = batch_seconds(p, bench, p.pages_per_request)
    gb_seconds = batches * per["total"] * (p.memory_mb / 1024)
    statements = math.ceil(pages * rows_per_page(p) / p.rows_per_statement)
    requests = statements
    compute_hours = statements * p.statement_seconds / 3600
    fn = function_cost(gb_seconds, prices)
    sql = sql_cost(0.0, compute_hours, requests, prices)
    return {"gb_seconds": gb_seconds, "functions": fn, "sql": sql["total"], "total": fn + sql["total"]}


def containers_monthly(vcpu: float, gib: float, prices: dict, instances: int = 1) -> float:
    return HOURS_PER_MONTH * (vcpu * prices["usd_per_vcpu_hour"] + gib * prices["usd_per_gib_hour"]) * instances


# ---- criteria -------------------------------------------------------------------------------------------------


def evaluate(p: Params, limits: dict, bench: dict) -> list[dict]:
    """G1-G6 exactly as pre-registered."""
    lim_sql = limits["forge_sql"]["stored_bytes_per_installation_production"]
    q = limits["confluence_rest_quota"]
    f = limits["forge_functions"]
    prices = limits["forge_prices"]
    out: list[dict] = []

    frac250 = storage_fraction(p, 250_000, lim_sql)
    out.append({"id": "G1", "text": "Index for 250k pages at most 50 % of the SQL limit",
                "result": f"{frac250 * 100:.1f} % ({storage_bytes(p, 250_000) / 1e6:.0f} MB)", "pass": frac250 <= 0.5})

    b50 = batch_seconds(p, bench, 50)
    budget = f["timeout_seconds_async_and_scheduled_max"] / 5
    out.append({"id": "G2", "text": "A 50-page batch takes at most 1/5 of the 900 s timeout",
                "result": f"{b50['total']:.1f} s of {budget:.0f} s", "pass": b50["total"] <= budget})

    pts = scan_points(50_000, p.pages_per_request)
    t1_best = scan_hours(pts, q["tier1_global_pool_points_per_hour_per_app"], p.pool_share_best)
    t1_plan = scan_hours(pts, q["tier1_global_pool_points_per_hour_per_app"], p.pool_share_plan)
    t2_pool = tier2_pool_per_hour(q["tier2_per_tenant_standard"]["base_points_per_hour"], q["tier2_per_tenant_standard"]["points_per_user_per_hour"], p.users)
    t2 = scan_hours(pts, t2_pool, 1.0)
    cb = compute_bound_hours(p, bench, 50_000)
    worst = max(t1_best, t1_plan, t2, cb)
    out.append({"id": "G3", "text": "First scan of 50k pages within 24 h (Tier 1 at 100 % and 20 %, Tier 2 Standard)",
                "result": f"{t1_best:.2f} h / {t1_plan:.2f} h / {t2:.2f} h (consumers alone: {cb * 60:.1f} min)", "pass": worst <= 24})

    ss = steady_state_monthly(p, prices, 50_000, free=False)
    out.append({"id": "G4", "text": "Steady-state Forge cost at 50k pages at most 5 % of $830 net, no free allowance",
                "result": f"${ss['total']:.2f} / month ({ss['total'] / p.net_revenue * 100:.3f} %)", "pass": ss["total"] <= 0.05 * p.net_revenue})

    # G5: one event = fetch changed page + fetch a few partner bodies + signature + a couple of SQL statements
    event_s = 3 * p.request_seconds + forge_us_per_page(p, bench) * 3 / 1e6 + 2 * p.statement_seconds
    out.append({"id": "G5", "text": "One incremental event fits the 55 s default timeout",
                "result": f"{event_s:.1f} s (3 REST calls at {p.request_seconds:g} s, 2 SQL statements)",
                "pass": event_s <= f["timeout_seconds_async_and_scheduled_default"]})

    out.append({"id": "G6", "text": "Manifest has no remotes, external fetch, Connect modules, providers or dynamic web triggers",
                "result": "by construction (criteria are search-reported)", "pass": True})
    return out


def gate_sentence(p: Params, limits: dict) -> str:
    lim_sql = limits["forge_sql"]["stored_bytes_per_installation_production"]
    n50 = max_pages_within(p, 0.5, lim_sql)
    n100 = max_pages_within(p, 1.0, lim_sql)
    return (f"Forge-only supports up to about {n50 // 1000}k pages per tenant with at least 50 % storage headroom "
            f"({n100 // 1000}k at the hard 1 GiB limit) with Architecture X; ESTIMATED")
