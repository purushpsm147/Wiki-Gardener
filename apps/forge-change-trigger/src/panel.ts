import { resultKey } from "./app";
import type { StoredResult } from "./app";
import type { Conflict } from "./core";

/** The viewer-bound capabilities the panel resolver needs. In Forge these use `api.asUser()`. */
export interface PanelDeps {
  kvs: { get<T>(key: string): Promise<T | undefined> };
  /** Whether the *viewing user* can read this page right now (amendment A06). */
  viewerCanRead(pageId: string): Promise<boolean>;
}

export type PanelData =
  | { state: "none" }
  | {
      state: "ok";
      version: number;
      detectedAt: string;
      latency: StoredResult["latency"];
      conflicts: Conflict[];
      /** Conflicts withheld because the viewer cannot read the approved page they quote. Only counted, never described. */
      hidden: number;
    };

/**
 * What the Conflict Radar byline item shows. Stored results are NOT an authorization layer: every quote from an approved page is
 * released only after re-checking, as the viewing user and at read time, that they can read that page. If the check fails or errors,
 * the conflict is hidden (fail closed) and only counted.
 */
export async function getPanelData(pageId: string, deps: PanelDeps): Promise<PanelData> {
  const stored = await deps.kvs.get<StoredResult>(resultKey(pageId));
  if (!stored) return { state: "none" };

  const allowed = new Map<string, boolean>();
  const visible: Conflict[] = [];
  let hidden = 0;
  for (const c of stored.conflicts) {
    const id = c.approved.pageId;
    if (!allowed.has(id)) {
      let ok = false;
      try {
        ok = await deps.viewerCanRead(id);
      } catch {
        ok = false;
      }
      allowed.set(id, ok);
    }
    if (allowed.get(id)) visible.push(c);
    else hidden++;
  }
  return { state: "ok", version: stored.version, detectedAt: stored.detectedAt, latency: stored.latency, conflicts: visible, hidden };
}
