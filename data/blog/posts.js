// data.blog.posts: every blog post, newest first, with a few values the layouts need:
//
//   body     the post's HTML, with URL-as-text links shortened (see shortLinks below) and relative
//            src/href (files next to index.md) made root-relative, so they work on any page
//   image    its first photo (photos/images front matter, else the first <img>), or null
//   preview  the card for its first external link, from data/link_previews.json, or null
//
// A post is any listed page under /blog/: the same rule as the feed in content/blog/index.md, so the
// blog page, post pages, archive, photos, /blog/atom.xml and the feeds written by
// tools/build_extras.py all agree.
export default function posts() {
    const previews = data.link_previews || {};
    return site.pages
        .filter((p) => /^\/blog\/.+/.test(p.path) && !p.unlisted && !p.draft)
        .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
        .map((p) => {
            const body = shortLinks(rootRelative(p.content || "", assetDir(p.path)));
            return {
                ...p,
                body,
                image: firstImage(p, body) || null,
                preview: previews[p.path] && previews[p.path].title ? previews[p.path] : null,
            };
        });
}

// Where HyperTemplates copies a post's files: /blog/x/slug.html (ugly_url) -> /blog/x/slug/
function assetDir(path) {
    return path.endsWith(".html") ? path.slice(0, -".html".length) + "/" : path.replace(/[^/]*$/, "");
}

function rootRelative(html, dir) {
    return html.replace(/(\s(?:src|href)=")(?![a-z][a-z0-9+.-]*:|\/|#)([^"]*)"/gi, (m, attr, url) => `${attr}${dir}${url}"`);
}

// `photos`/`images` front matter (Micro.blog imports), else the first <img> in the post.
function firstImage(p, body) {
    for (const list of [p.photos, p.images]) {
        if (Array.isArray(list) && list.length) return String(list[0]);
    }
    const m = /<img\s[^>]*?src="([^"]+)"/.exec(body);
    return m ? m[1].replace(/&amp;/g, "&") : "";
}

// Links whose text is the URL itself (possibly cut by Micro.blog: "friendo.monster/posts/the…")
// show a short bare URL instead, with the full URL on hover:
//   <a href="https://www.theverge.com/entertainment/953596/google-...">https://www.theverge.com/…</a>
//   -> <a href="…" title="https://www.theverge.com/…">www.theverge.com/entertainment/953596/go…</a>
const MAX_LINK_CHARS = 40;

function shortLinks(html) {
    return html.replace(/<a(\s[^>]*)>([^<]*)<\/a>/g, (whole, attrs, text) => {
        if (/data-hyper-mention/.test(attrs)) return whole; // @mentions and #hashtags
        const href = /\shref="([^"]*)"/.exec(attrs);
        if (!href) return whole;
        const dest = decode(href[1]);
        const bareDest = bare(dest);
        const bareText = bare(decode(text).trim().replace(/(\.\.\.|…)$/, ""));
        if (!bareText || !bareDest.startsWith(bareText)) return whole;
        let short = bareDest;
        if ([...short].length > MAX_LINK_CHARS) short = [...short].slice(0, MAX_LINK_CHARS).join("") + "…";
        const title = /\stitle=/.test(attrs) ? "" : ` title="${escape(dest)}"`;
        return `<a${attrs}${title}>${escape(short)}</a>`;
    });
}

function bare(url) {
    return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

function decode(s) {
    return s.replace(/&amp;/g, "&").replace(/&#39;|&#x27;/g, "'").replace(/&quot;|&#34;/g, '"').replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&hellip;/g, "…");
}

function escape(s) {
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
