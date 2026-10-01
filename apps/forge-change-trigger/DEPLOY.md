# Running the GATE-S3 demo on a real Confluence site

**Status: not done.** The sandbox this spike was written in has no Atlassian account and blocks `*.atlassian.com`, so the live demo
could not be run and no latency was measured. Everything that can be tested without Atlassian is tested (`npm test`). This file is the
exact local procedure; it takes about 30 minutes. Paste what it produces into
[the spike document](../../docs/spikes/03-change-time-trigger-poc.md#live-demo-results-todo).

Evidence labels: **VERIFIED** means read or run in this repository (the Forge CLI help below is from `@forge/cli@14.1.0`, 2026-10-01).
**ASSUMED** means it has not been observed against a real site. Every command below exists with these flags (VERIFIED, `--help`);
what each one does against a real site is ASSUMED.

## What you need

- Node 22 or newer, and this directory: `cd apps/forge-change-trigger && npm ci`
- An Atlassian account and a Confluence Cloud site where you may create pages and spaces. `npx forge site provision` provisions a
  demo site for development (VERIFIED it exists; whether it includes Confluence is ASSUMED, so a free Confluence Cloud site is the
  fallback).
- An API token for the seed script: <https://id.atlassian.com/manage-profile/security/api-tokens> (ASSUMED location).
- A second user on the site who can view the demo space but will be denied one page (step 9), if you want to test amendment A06.

Use `npx forge`, not a global install; the CLI is a dev dependency.

## Steps

**1. Log in.** `npx forge login` (opens a browser), or `npx forge login -u you@example.com -t <api token>`.

**2. Register the app.** `npx forge register conflict-radar-s3`. This replaces the placeholder `app.id` in `manifest.yml` with a real
one. **Do not commit that change**: `test/manifest.test.ts` fails if a real id is committed. Before committing anything run
`git checkout -- manifest.yml`.

**3. Lint.** `npx forge lint`. It needs the login (VERIFIED: it refuses without one), so this is the first time the platform's own
linter sees the manifest. Offline, `@forge/manifest`'s validator already accepts it (`npm test`). Expect no errors; any error is a
finding.

**4. Create the demo pages.** Create a space (key `DEMO`, or any key) in the site, then
`ATLASSIAN_API_TOKEN=... npx tsx scripts/seed-site.ts --site <your-site>.atlassian.net --email <you> --space-key DEMO`
(add `--dry-run` first to see the plan; add `--prefix "S3 demo: "` if a title collides). It creates the ten fixture pages at version
1 and prints the next two commands. UNTESTED against a real site; if the REST call fails, create the ten pages by pasting each
`test/fixtures/pages/*.v1.html` through the Markup macro, or by hand, and note the three approved pages' ids from their URLs.

**5. Configure.** Using the ids printed by step 4:

```
npx forge variables set -e development APPROVED_SOURCE_PAGE_IDS <policy-data-retention id>,<policy-access-control id>,<policy-incident-response id>
npx forge variables set -e development LOG_EVENT_PAYLOAD true
```

`LOG_EVENT_PAYLOAD=true` makes the first runs log the raw event, which is how the payload shape gets verified. If the CLI says the
change needs a deploy, run step 6 again afterwards. Whether `variables set` works before the first deploy is ASSUMED; if it errors,
do step 6 first.

**6. Deploy and install.**

```
npx forge deploy -e development
npx forge install -e development -p Confluence -s <your-site>.atlassian.net
```

The webpack bundling inside `forge deploy` has never been run on this code (it needs the login), so a bundling error here is a
finding, not a typo to hide. The install asks you to confirm the scopes: four read-only scopes and app storage, no write scope.
Install **after** step 4, or the ten page creations are processed too.

**7. Run the demo (GATE-S3).** In the site, open *Runbook: Log Rotation*, edit it, change `Application logs are retained for 90 days.`
to `... 30 days.`, and click **Update**. Note the wall-clock time you clicked. Then:

```
npx forge logs -e development -s 15m | grep conflict-radar
```

You should see, in this order: an `event-probe` line (the raw payload), a `conflict-radar.result` line with `"conflicts":1` and a
`latency` object, and a `conflict-radar.conflict` line whose `edited.quote` is `Application logs are retained for 30 days.` with
`start` 69 and `end` 111, and whose `approved.quote` is `Application logs must be retained for 90 days.` with `start` 123 and
`end` 169, `approved.page` being the policy page's id. `latency.versionToDetectedMs` is the time from Confluence saving the version
to the app finishing; `eventToDetectedMs` is from the platform emitting the event. **GATE-S3 passes live if that happens within a few
minutes of the click.** Then open the runbook: the **Conflict Radar** byline item shows the same two quotes with offsets.

Do the other two planted edits the same way (the expected quotes are in `test/fixtures/dataset.json`): in *Runbook: Production
Access* add `A VPN connection is not required for read-only production access.` as a new last paragraph, and in *Runbook: Sev1
On-call* change `within 15 minutes` to `within 30 minutes`. (The fixtures hold both edited versions: `*.v2.html`.)

**8. Measure latency properly.** Alternate the log-rotation edit between `90 days` and `30 days` twenty times (ten conflicts, ten
repairs), waiting for each to settle. For every edit record `latency.versionToDetectedMs` and `latency.eventToDetectedMs` from the
log line, and your own stopwatch from click to the line appearing. The Forge function clock and Confluence's `createdAt` clock can
differ by a little; the stopwatch is the cross-check. Report min, median, max.

**9. Check amendment A06 (the viewer's live permissions).** Restrict the *Data Retention Policy (Approved)* page so a second user
cannot view it. As that user, open *Runbook: Log Rotation* with the 30-day edit in place. Expected: the panel says
`1 conflict(s) withheld` and shows neither the policy's title, its quote nor `90 days`. Then, as the first user, lift the restriction
and reload: the conflict appears without any new edit (the check is live, at read time). Also confirm the first use of the panel by
a user does not need a consent step that breaks it (ASSUMED that `api.asUser()` works from a resolver with these scopes).

**10. Check Runs on Atlassian eligibility.** `npx forge eligibility -e development`. This closes S2's criterion G6, which rests on
search-reported criteria; the manifest has no remotes, providers, Connect modules or external permissions by construction
(`test/manifest.test.ts`).

**11. Clean up.** `npx forge uninstall -e development -s <site> -p Confluence`; delete the demo pages or space;
`git checkout -- manifest.yml`; revoke the API token.

## What to send back

A block like this, pasted into the spike document's *Live demo results* section:

```
date / forge cli version / site type (free? demo?):
step 3  forge lint:                  ok | errors: ...
step 6  forge deploy:                ok | errors: ...
step 7  conflict logged:             yes | no     offsets as expected: yes | no (actual: ...)
        raw event payload (paste the event-probe line, with ids redacted if you prefer):
        updateTrigger value(s) seen:  ...
        did an event fire for the REST-created pages in step 4 (only if installed first)?: ...
step 8  versionToDetectedMs (ms):    ...   min / median / max: ...
        eventToDetectedMs (ms):      ...   min / median / max: ...
        stopwatch click-to-log (s):  ...
        did an event fire for a repair edit? did two quick edits produce two events?: ...
step 9  A06 withheld for the second user: yes | no     appeared after the restriction was lifted: yes | no
step 10 forge eligibility:           eligible | not eligible: reasons ...
anything surprising:
```

## What this file does not cover

Editing in Confluence's live-edit mode, where there may be no explicit Update click (does the event fire per autosave, per
publish, or never?); a space with thousands of pages; two approved sources that disagree with each other; the reverse direction
(an *approved* page changes and the pages that now disagree with it need finding), which this app skips and which needs the S2
index. Each is listed in the spike document as unproven.
