import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { decodeEntities, storageToText } from "../src/core";
import { storageOf } from "./helpers";

describe("decodeEntities", () => {
  it("decodes named, decimal and hex entities and leaves unknown ones alone", () => {
    assert.equal(decodeEntities("a &amp; b &lt;c&gt; &quot;d&quot; &#8217; &#x27;"), `a & b <c> "d" ’ '`);
    assert.equal(decodeEntities("&nosuchentity; &#99999999;"), "&nosuchentity; &#99999999;");
  });
  it("turns a non-breaking space into an ordinary one", () => {
    assert.equal(decodeEntities("a&nbsp;b"), "a b");
  });
});

describe("storageToText", () => {
  it("makes block boundaries into newlines and drops inline tags", () => {
    const text = storageToText("<h1>Title</h1><p>One <strong>bold</strong> word.</p><ul><li>A</li><li>B</li></ul>");
    assert.equal(text, "Title\nOne bold word.\nA\nB");
  });

  it("collapses runs of spaces, trims lines and drops empty lines", () => {
    assert.equal(storageToText("<p>  a   b  </p>\n\n<p> </p><p>c</p>"), "a b\nc");
  });

  it("drops code bodies, macro parameters and comments but keeps rich-text bodies", () => {
    const html =
      '<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">yaml</ac:parameter>' +
      "<ac:plain-text-body><![CDATA[retention: 7 days]]></ac:plain-text-body></ac:structured-macro>" +
      '<ac:structured-macro ac:name="info"><ac:rich-text-body><p>Keep this.</p></ac:rich-text-body></ac:structured-macro><!-- gone -->';
    assert.equal(storageToText(html), "Keep this.");
  });

  it("unwraps CDATA link text", () => {
    assert.equal(storageToText('<p>See <ac:link><ac:plain-text-link-body><![CDATA[the policy]]></ac:plain-text-link-body></ac:link>.</p>'), "See the policy.");
  });

  it("handles <br> as a line break, and a table row as one line of cells joined by ' | '", () => {
    assert.equal(storageToText("<p>a<br/>b</p><table><tr><td>c</td><td>d</td></tr></table>"), "a\nb\nc | d");
  });

  it("reads Confluence tables, where every cell wraps a paragraph", () => {
    const html =
      "<table><tbody><tr><th><p>Log type</p></th><th><p>Retention</p></th></tr>" +
      "<tr><td><p>Application logs</p></td><td><p>90 days</p></td></tr><tr><td><p>Audit logs</p></td><td><p>365 days</p></td></tr></tbody></table>";
    assert.equal(storageToText(html), "Log type | Retention\nApplication logs | 90 days\nAudit logs | 365 days");
  });

  it("joins a cell's own paragraphs and line breaks with a space, and drops empty cells", () => {
    assert.equal(storageToText("<table><tr><td><p>One</p><p>two<br/>three</p></td><td></td><td> </td><td>four</td></tr></table>"), "One two three | four");
  });

  it("leaves text around a table on its own lines", () => {
    assert.equal(storageToText("<p>Before.</p><table><tr><td>a</td><td>b</td></tr></table><p>After.</p>"), "Before.\na | b\nAfter.");
  });

  it("ignores the code macro in the architecture fixture, so its 7 days never reach the detector", () => {
    const text = storageToText(storageOf("arch-overview", "v1"));
    assert.ok(!text.includes("7 days"));
    assert.ok(text.includes("Logs are shipped to the central log store."));
  });

  it("is a no-op on text that is already normalized", () => {
    const text = storageToText(storageOf("policy-data-retention", "v1"));
    assert.equal(storageToText(text), text);
  });

  it("is deterministic, which is what makes character offsets meaningful", () => {
    const a = storageToText(storageOf("runbook-log-rotation", "v2"));
    const b = storageToText(storageOf("runbook-log-rotation", "v2"));
    assert.equal(a, b);
  });
});
