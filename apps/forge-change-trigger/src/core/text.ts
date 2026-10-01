const ENTITIES: Record<string, string> = {
  amp: "&",
  lt: "<",
  gt: ">",
  quot: '"',
  apos: "'",
  nbsp: " ",
  ndash: "–",
  mdash: "—",
  hellip: "…",
  lsquo: "‘",
  rsquo: "’",
  ldquo: "“",
  rdquo: "”",
};

export function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);/g, (whole, body: string) => {
    if (body.startsWith("#")) {
      const code = body[1] === "x" || body[1] === "X" ? parseInt(body.slice(2), 16) : parseInt(body.slice(1), 10);
      return Number.isFinite(code) && code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : whole;
    }
    return ENTITIES[body] ?? whole;
  });
}

/**
 * Reduce Confluence storage-format XHTML to normalized plain text.
 *
 * Every offset the detector reports is an offset into this text, not into the storage format. Rules:
 *  - code bodies (`ac:plain-text-body`), macro parameters and placeholders are dropped;
 *  - each table row becomes one line, its cells joined by " | " (so a row such as "Application logs | 90 days" can be compared with a
 *    sentence; a cell's own paragraphs are joined by a space), and empty cells are dropped;
 *  - other block boundaries (paragraphs, list items, headings, `<br>`) become a single newline;
 *  - other tags are removed, entities decoded, runs of spaces collapsed, lines trimmed, empty lines dropped.
 */
export function storageToText(html: string): string {
  let s = html;
  s = s.replace(/<!--[\s\S]*?-->/g, " ");
  s = s.replace(/<ac:plain-text-body>[\s\S]*?<\/ac:plain-text-body>/g, " ");
  s = s.replace(/<ac:parameter\b[^>]*>[\s\S]*?<\/ac:parameter>/g, " ");
  s = s.replace(/<ac:placeholder\b[^>]*>[\s\S]*?<\/ac:placeholder>/g, " ");
  s = s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1");
  s = s.replace(/<tr\b[^>]*>([\s\S]*?)<\/tr\s*>/gi, (_row, inner: string) => {
    const cells = [...inner.matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]\s*>/gi)]
      .map((m) => m[1]!.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim())
      .filter((cell) => cell.length > 0);
    return `\n${cells.join(" | ")}\n`;
  });
  s = s.replace(/<\s*br\s*\/?\s*>/gi, "\n");
  s = s.replace(
    /<\/\s*(?:p|div|li|ul|ol|h[1-6]|tr|table|th|td|blockquote|pre|ac:task|ac:task-body|ac:rich-text-body|ac:structured-macro)\s*>/gi,
    "\n",
  );
  s = s.replace(/<[^>]*>/g, "");
  s = decodeEntities(s);
  return s
    .split(/\r?\n/)
    .map((line) => line.replace(/[ \t\f\v ]+/g, " ").trim())
    .filter((line) => line.length > 0)
    .join("\n");
}
