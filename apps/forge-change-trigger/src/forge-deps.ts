// The only file that binds the app to Forge runtime APIs. Everything it calls is covered by unit tests through fakes, except the
// two lines that actually touch @forge/api and @forge/kvs; those can only be exercised on a deployed app (see DEPLOY.md).
import api, { assumeTrustedRoute } from "@forge/api";
import kvs from "@forge/kvs";
import type { Deps } from "./app";
import type { PanelDeps } from "./panel";
import { canRead, getPage } from "./confluence";
import type { Requester } from "./confluence";

// `path` is built by confluence.ts from an encodeURIComponent'ed id and fixed text, so trusting it as a Route is safe.
const asApp: Requester = (path) => api.asApp().requestConfluence(assumeTrustedRoute(path));
const asViewer: Requester = (path) => api.asUser().requestConfluence(assumeTrustedRoute(path));

export function approvedIdsFromEnv(value: string | undefined): string[] {
  return (value ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

export function appDeps(): Deps {
  return {
    getPage: (id, opts) => getPage(asApp, id, opts),
    kvs: { set: (key, value) => kvs.set(key, value as never), get: <T>(key: string) => kvs.get<T>(key) },
    approvedIds: approvedIdsFromEnv(process.env.APPROVED_SOURCE_PAGE_IDS),
    now: () => new Date(),
    log: (line) => console.log(line),
    probe: process.env.LOG_EVENT_PAYLOAD === "true",
  };
}

export function viewerDeps(): PanelDeps {
  return {
    kvs: { get: <T>(key: string) => kvs.get<T>(key) },
    viewerCanRead: (pageId) => canRead(asViewer, pageId),
  };
}
