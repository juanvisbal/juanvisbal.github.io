// excerpt turns HTML (or Markdown-rendered HTML) into plain text, cut at a word boundary.
// Same rule as Hugo's `plainify | htmlUnescape | truncate N`: "Some long text …".
//
// usage: ${ excerpt(page.summary, page.content, "160") }  (the first non-empty text is used)
export default function excerpt(...args) {
    const max = Number(args.pop()) || 160;
    const html = args.find((a) => typeof a === "string" && a.trim() !== "") || "";
    const text = [...plain(html)];
    if (text.length <= max) return text.join("");
    // Keep every whole word that fits: the word ending at `max` counts if a space follows it.
    const cut = text.slice(0, max + 1).join("");
    const space = cut.lastIndexOf(" ");
    return (space > 0 ? cut.slice(0, space) : cut.slice(0, -1)) + " …";
}

function plain(html) {
    return html
        .replace(/<br\s*\/?>|<\/(p|li|h[1-6]|blockquote|div)>/gi, " ")
        .replace(/<[^>]*>/g, "")
        .replace(/&(#x?[0-9a-f]+|[a-z]+);/gi, (m, e) => {
            const named = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", hellip: "…", rsquo: "’", lsquo: "‘", rdquo: "”", ldquo: "“", mdash: "—", ndash: "–" };
            if (e[0] !== "#") return named[e.toLowerCase()] ?? m;
            const code = e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
            return Number.isFinite(code) ? String.fromCodePoint(code) : m;
        })
        .replace(/\s+/g, " ")
        .trim();
}
