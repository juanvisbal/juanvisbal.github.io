// now_cards turns the Now page's content into cards: each "## Heading" and what follows it becomes
// a <section>, with an optional Font Awesome icon per heading (`icons` front matter) and full
// width for headings listed in `wide`.
//
// usage: ${ now_cards(page.content, page.icons, page.wide) }
export default function now_cards(html, icons, wide) {
    const parts = String(html || "").split(/(?=<h2[\s>])/);
    const cards = [];
    for (const part of parts) {
        const m = /^<h2[^>]*>([\s\S]*?)<\/h2>([\s\S]*)$/.exec(part);
        if (!m) continue; // anything before the first heading
        const title = m[1].replace(/<[^>]*>/g, "").trim();
        const icon = icons && icons[title] ? `<i class="fa-solid ${icons[title]}"></i> ` : "";
        const isWide = Array.isArray(wide) && wide.includes(title);
        cards.push(`<section class="now-section${isWide ? " now-section--wide" : ""}">
          <h3>${icon}${m[1].trim()}</h3>
          ${m[2].trim()}
        </section>`);
    }
    return cards.join("\n        ");
}
