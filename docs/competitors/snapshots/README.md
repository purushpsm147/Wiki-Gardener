# Snapshots

**No baseline has been taken yet.** `latest.json` and `latest.md` do not exist.

Why: the environment that built the watcher cannot reach `marketplace.atlassian.com`, `*.atlassian.com`, `k-ai.ai` or `evergreen.team`
(the egress proxy refuses them: `EGRESS_BLOCKED`, `Tunnel connection failed: 403`; VERIFIED 2026-10-01 with the tool's own run, which
failed all six enabled sources with that reason and exit code 2, and with `WebFetch`). The policy is left alone: the baseline is taken
somewhere that is allowed to reach them.

Either of these takes it:

```
python tools/competitor-watch/watch.py run --raw-dir /tmp/competitor-raw
git add docs/competitors/snapshots && git commit -m "competitor-watch: baseline"
```

or, once the workflow is on the default branch, *Actions* → *competitor-watch* → *Run workflow*.

After that this directory holds `latest.json` (the data, stable key order, small diffs) and `latest.md` (generated: do not edit; it
includes the *Differentiation thesis status* table). Git history is the archive; every change to the world is one commit.

The first real run also tells whether the extractor's guesses about Marketplace layouts were right. See the **Health** table in
`latest.md`, and [`docs/spikes/04-competitor-watch.md`](../../spikes/04-competitor-watch.md#what-to-check-on-the-first-real-run).
