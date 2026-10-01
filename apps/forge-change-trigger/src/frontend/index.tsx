import React, { useEffect, useState } from "react";
import ForgeReconciler, { Code, Heading, Inline, Lozenge, SectionMessage, Spinner, Stack, Strong, Text } from "@forge/react";
import { invoke } from "@forge/bridge";
import type { PanelData } from "../panel";

// `invoke` is typed as `T | { body: T, metadata? }`; the wrapper only appears when metadata is requested, which this app never does.
function unwrap(r: unknown): PanelData {
  if (typeof r === "object" && r !== null && "body" in r && !("state" in r)) return (r as { body: PanelData }).body;
  return r as PanelData;
}

function seconds(ms: number | undefined): string | undefined {
  return ms === undefined ? undefined : `${(ms / 1000).toFixed(1)} s`;
}

const App = () => {
  const [data, setData] = useState<PanelData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    invoke<PanelData>("getConflicts")
      .then((r) => setData(unwrap(r)))
      .catch((e: unknown) => setError(String(e)));
  }, []);

  if (error) return <SectionMessage appearance="error" title="Conflict Radar could not load"><Text>{error}</Text></SectionMessage>;
  if (!data) return <Spinner />;
  if (data.state === "none") return <Text>No check has run for this page yet. Edit and publish it to trigger one.</Text>;

  const afterEdit = seconds(data.latency.versionToDetectedMs);
  return (
    <Stack space="space.150">
      <Heading size="small">Conflict Radar</Heading>
      <Text>
        Version {data.version}, checked {data.detectedAt}
        {afterEdit ? `, ${afterEdit} after the edit was saved` : ""}.
      </Text>
      {data.conflicts.length === 0 && data.hidden === 0 ? (
        <SectionMessage appearance="success" title="No conflicts">
          <Text>This edit does not disagree with any approved source.</Text>
        </SectionMessage>
      ) : null}
      {data.hidden > 0 ? (
        <SectionMessage appearance="warning" title={`${data.hidden} conflict(s) withheld`}>
          <Text>They quote a page you do not have permission to read.</Text>
        </SectionMessage>
      ) : null}
      {data.conflicts.map((c) => (
        <Stack key={c.id} space="space.050">
          <Inline space="space.100">
            <Lozenge appearance="removed">{c.kind}</Lozenge>
            <Text>{c.explanation}</Text>
          </Inline>
          <Text>
            <Strong>This page</Strong> (characters {c.changed.start} to {c.changed.end}): <Code>{c.changed.quote}</Code>
          </Text>
          <Text>
            <Strong>{c.approved.title}</Strong> (characters {c.approved.start} to {c.approved.end}): <Code>{c.approved.quote}</Code>
          </Text>
        </Stack>
      ))}
    </Stack>
  );
};

ForgeReconciler.render(<React.StrictMode><App /></React.StrictMode>);
