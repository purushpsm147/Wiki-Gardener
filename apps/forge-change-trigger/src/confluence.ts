/**
 * A thin client over the Confluence Cloud REST API v2. It knows nothing about Forge: it is given a `Requester`, so tests can pass a
 * mock and the Forge entry points pass `api.asApp()` or `api.asUser()`.
 *
 * Response shape, VERIFIED from the `confluence.js@3.2.0` type definitions (generated from Atlassian's OpenAPI):
 *   GET /wiki/api/v2/pages/{id}?body-format=storage[&version=N]
 *   -> { id, status, title, spaceId, version: { number, createdAt, ... }, body: { storage: { representation, value } } }
 */

export interface HttpResponse {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
  text(): Promise<string>;
}

/** Performs a GET against Confluence for a path such as `/wiki/api/v2/pages/123?body-format=storage`. */
export type Requester = (path: string) => Promise<HttpResponse>;

export interface PageDoc {
  id: string;
  status?: string;
  title: string;
  spaceId?: string;
  version: { number: number; createdAt?: string };
  /** Storage-format XHTML. Empty when the page has no body. */
  storage: string;
}

export class ConfluenceError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ConfluenceError";
    this.status = status;
  }
}

function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null;
}

/** Validates the fields this app relies on and fails loudly, naming the field, if the response is not what was expected. */
export function parsePage(json: unknown): PageDoc {
  if (!isRecord(json)) throw new ConfluenceError(0, "page response is not an object");
  const id = json.id;
  if (typeof id !== "string" && typeof id !== "number") throw new ConfluenceError(0, "page response has no id");
  const title = json.title;
  if (typeof title !== "string") throw new ConfluenceError(0, `page ${String(id)} has no title`);
  const version = json.version;
  if (!isRecord(version) || typeof version.number !== "number") throw new ConfluenceError(0, `page ${String(id)} has no version.number`);
  const body = json.body;
  const storage = isRecord(body) && isRecord(body.storage) && typeof body.storage.value === "string" ? body.storage.value : "";
  const doc: PageDoc = { id: String(id), title, version: { number: version.number }, storage };
  if (typeof json.status === "string") doc.status = json.status;
  if (typeof json.spaceId === "string" || typeof json.spaceId === "number") doc.spaceId = String(json.spaceId);
  if (typeof version.createdAt === "string") doc.version.createdAt = version.createdAt;
  return doc;
}

async function bodyOf(res: HttpResponse): Promise<string> {
  try {
    return (await res.text()).slice(0, 300);
  } catch {
    return "";
  }
}

/** The page at its current version, or at `opts.version`. Returns null when it does not exist (or is not visible to the caller). */
export async function getPage(request: Requester, id: string, opts: { version?: number } = {}): Promise<PageDoc | null> {
  const q = new URLSearchParams({ "body-format": "storage" });
  if (opts.version !== undefined) q.set("version", String(opts.version));
  const res = await request(`/wiki/api/v2/pages/${encodeURIComponent(id)}?${q.toString()}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new ConfluenceError(res.status, `GET page ${id} failed: HTTP ${res.status} ${await bodyOf(res)}`);
  return parsePage(await res.json());
}

/**
 * Whether the caller can read a page. Used with a *user* requester so that what is shown is gated by the viewer's live
 * permissions (amendment A06), never by anything stored at ingest. 403 and 404 mean no. Anything else throws, and callers fail closed.
 */
export async function canRead(request: Requester, id: string): Promise<boolean> {
  const res = await request(`/wiki/api/v2/pages/${encodeURIComponent(id)}`);
  if (res.status === 403 || res.status === 404) return false;
  if (!res.ok) throw new ConfluenceError(res.status, `permission check for page ${id} failed: HTTP ${res.status}`);
  return true;
}
