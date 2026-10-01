import type { PageDoc } from "./confluence";
import { analyzeEdit, storageToText } from "./core";
import type { Conflict, PageText, Span } from "./core";

/** What the app needs from the outside world. Forge supplies real ones (`forge-deps.ts`); tests supply fakes. */
export interface Deps {
  getPage(id: string, opts?: { version?: number }): Promise<PageDoc | null>;
  kvs: {
    set(key: string, value: unknown): Promise<unknown>;
    get<T>(key: string): Promise<T | undefined>;
  };
  /** Page ids of the approved sources, from the `APPROVED_SOURCE_PAGE_IDS` environment variable. */
  approvedIds: string[];
  now(): Date;
  log(line: string): void;
  /** Log the raw event so its real shape can be checked on the first deploy. */
  probe?: boolean;
}

export const STORED_CONFLICT_LIMIT = 50;
export const resultKey = (pageId: string): string => `conflicts:${pageId}`;

export interface StoredResult {
  schema: 1;
  pageId: string;
  title: string;
  version: number;
  previousVersion: number | null;
  spans: Span[] | "all";
  changedSentences: number;
  conflicts: Conflict[];
  conflictsTruncated: boolean;
  approvedIds: string[];
  /** Approved ids that were not found or are not current (trashed, archived, draft): this edit was checked against nothing from them. */
  approvedMissing: string[];
  eventCreatedDate?: string;
  versionCreatedAt?: string;
  updateTrigger?: string;
  detectedAt: string;
  elapsedMs: number;
  latency: { eventToDetectedMs?: number; versionToDetectedMs?: number };
}

export interface ParsedEvent {
  pageId?: string;
  versionNumber?: number;
  eventCreatedDate?: string;
  updateTrigger?: string;
  selfGenerated?: boolean;
}

function rec(x: unknown): Record<string, unknown> | undefined {
  return typeof x === "object" && x !== null ? (x as Record<string, unknown>) : undefined;
}
const str = (x: unknown): string | undefined => (typeof x === "string" ? x : typeof x === "number" ? String(x) : undefined);

/**
 * Read the fields this app needs from a `avi:confluence:updated:page` event. The documented payload (search-reported) has `content`
 * (the page), `eventCreatedDate`, `updateTrigger`, `selfGenerated` and `atlassianId`; the exact shape of `content` is NOT verified,
 * so this accepts `content.id`, `page.id` and `pageId`. Set `LOG_EVENT_PAYLOAD=true` on the first deploy to log the raw event.
 */
export function parseEvent(event: unknown): ParsedEvent {
  const e = rec(event) ?? {};
  const content = rec(e.content) ?? rec(e.page) ?? {};
  const version = rec(content.version);
  const out: ParsedEvent = {};
  const pageId = str(content.id) ?? str(e.pageId);
  if (pageId) out.pageId = pageId;
  if (typeof version?.number === "number") out.versionNumber = version.number;
  const created = str(e.eventCreatedDate);
  if (created) out.eventCreatedDate = created;
  const trigger = str(e.updateTrigger);
  if (trigger) out.updateTrigger = trigger;
  if (typeof e.selfGenerated === "boolean") out.selfGenerated = e.selfGenerated;
  return out;
}

/**
 * The version to diff the latest one against. A page can gain several versions before an event is handled, and events can be handled
 * out of order, so "the version before the latest" would skip edits. Diff from the oldest of: the version before the latest, the
 * version before the one the event names, and the last version this app already checked. `null` means there is nothing to diff
 * against (a first version), which makes the whole page count as changed.
 */
export function baselineVersion(latest: number, eventVersion?: number, lastChecked?: number): number | null {
  if (latest <= 1) return null;
  let base = latest - 1;
  if (eventVersion !== undefined && eventVersion >= 1 && eventVersion <= latest) base = Math.min(base, eventVersion - 1);
  if (lastChecked !== undefined && lastChecked >= 1 && lastChecked < latest) base = Math.min(base, lastChecked);
  return base >= 1 ? base : null;
}

const toPageText = (p: PageDoc): PageText => ({ id: p.id, title: p.title, version: p.version.number, text: storageToText(p.storage) });

function msBetween(later: Date, earlier: string | undefined): number | undefined {
  if (!earlier) return undefined;
  const t = Date.parse(earlier);
  return Number.isFinite(t) ? later.getTime() - t : undefined;
}

/**
 * The whole change-time flow: a page was updated, so fetch it and its previous version, fetch the approved sources, check only the
 * changed spans, and store and log the result. Returns the stored result, or null when the event was skipped.
 */
export async function handlePageUpdated(event: unknown, deps: Deps): Promise<StoredResult | null> {
  const started = deps.now();
  if (deps.probe) deps.log(JSON.stringify({ msg: "conflict-radar.event-probe", event }));

  const parsed = parseEvent(event);
  if (!parsed.pageId) {
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: "no page id in event; set LOG_EVENT_PAYLOAD=true to see its shape" }));
    return null;
  }
  if (parsed.selfGenerated) {
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: "self-generated event", pageId: parsed.pageId }));
    return null;
  }
  if (deps.approvedIds.includes(parsed.pageId)) {
    // Re-checking the rest of the space against an edited approved source needs the index from Spike S2; not part of this demo.
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: "edited page is itself an approved source", pageId: parsed.pageId }));
    return null;
  }

  const current = await deps.getPage(parsed.pageId);
  if (!current) {
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: "page not found", pageId: parsed.pageId }));
    return null;
  }
  if (current.status !== undefined && current.status !== "current") {
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: `page status is ${current.status}`, pageId: current.id }));
    return null;
  }

  const earlier = await deps.kvs.get<StoredResult>(resultKey(current.id));
  const lastChecked = typeof earlier?.version === "number" ? earlier.version : undefined;
  if (lastChecked === current.version.number) {
    // Delivery may repeat, and an update need not create a version (`updateTrigger` has other causes). Neither needs another check.
    deps.log(JSON.stringify({ msg: "conflict-radar.skip", reason: "this version was already checked", pageId: current.id, version: lastChecked }));
    return null;
  }
  const base = baselineVersion(current.version.number, parsed.versionNumber, lastChecked);
  const previous = base === null ? null : await deps.getPage(current.id, { version: base });

  const approvedPages: PageDoc[] = [];
  const approvedMissing: string[] = [];
  for (const id of deps.approvedIds) {
    const p = await deps.getPage(id);
    // A trashed, archived or draft source is no longer approved text, so it counts as unavailable, like one that cannot be found.
    if (p && (p.status === undefined || p.status === "current")) approvedPages.push(p);
    else approvedMissing.push(id);
  }

  const analysis = analyzeEdit({
    previous: previous ? toPageText(previous) : null,
    current: toPageText(current),
    approved: approvedPages.map(toPageText),
  });

  const detected = deps.now();
  const result: StoredResult = {
    schema: 1,
    pageId: current.id,
    title: current.title,
    version: current.version.number,
    previousVersion: previous ? previous.version.number : null,
    spans: analysis.spans,
    changedSentences: analysis.changedSentences.length,
    conflicts: analysis.conflicts.slice(0, STORED_CONFLICT_LIMIT),
    conflictsTruncated: analysis.conflicts.length > STORED_CONFLICT_LIMIT,
    approvedIds: deps.approvedIds,
    approvedMissing,
    detectedAt: detected.toISOString(),
    elapsedMs: detected.getTime() - started.getTime(),
    latency: {},
  };
  if (parsed.eventCreatedDate) result.eventCreatedDate = parsed.eventCreatedDate;
  if (parsed.updateTrigger) result.updateTrigger = parsed.updateTrigger;
  if (current.version.createdAt) result.versionCreatedAt = current.version.createdAt;
  const e2d = msBetween(detected, parsed.eventCreatedDate);
  const v2d = msBetween(detected, current.version.createdAt);
  if (e2d !== undefined) result.latency.eventToDetectedMs = e2d;
  if (v2d !== undefined) result.latency.versionToDetectedMs = v2d;

  await deps.kvs.set(resultKey(current.id), result);

  deps.log(
    JSON.stringify({
      msg: "conflict-radar.result",
      pageId: result.pageId,
      version: result.version,
      conflicts: analysis.conflicts.length,
      changedSentences: result.changedSentences,
      elapsedMs: result.elapsedMs,
      latency: result.latency,
      approvedMissing,
    }),
  );
  for (const c of analysis.conflicts) {
    deps.log(
      JSON.stringify({
        msg: "conflict-radar.conflict",
        id: c.id,
        kind: c.kind,
        severity: c.severity,
        explanation: c.explanation,
        edited: { page: c.changed.pageId, quote: c.changed.quote, start: c.changed.start, end: c.changed.end },
        approved: { page: c.approved.pageId, quote: c.approved.quote, start: c.approved.start, end: c.approved.end },
      }),
    );
  }
  return result;
}
