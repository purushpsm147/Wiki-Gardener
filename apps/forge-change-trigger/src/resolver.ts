import Resolver from "@forge/resolver";
import { viewerDeps } from "./forge-deps";
import { getPanelData } from "./panel";

interface InvokeContext {
  extension?: { content?: { id?: string }; page?: { id?: string } };
}

const resolver = new Resolver();

// The page being viewed comes from the platform's context, never from the caller's payload.
resolver.define("getConflicts", async (req) => {
  const context = req.context as InvokeContext | undefined;
  const pageId = context?.extension?.content?.id ?? context?.extension?.page?.id;
  if (!pageId) return { state: "none" };
  return getPanelData(String(pageId), viewerDeps());
});

export const handler = resolver.getDefinitions();
