import { handlePageUpdated } from "./app";
import { appDeps } from "./forge-deps";

/** Entry point for the page created and page updated triggers (manifest function `on-page-updated`). */
export async function onPageUpdated(event: unknown): Promise<void> {
  await handlePageUpdated(event, appDeps());
}
