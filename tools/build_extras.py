#!/usr/bin/env python3
"""The parts of the site HyperTemplates doesn't build itself. Run by tools/build.sh.

  tools/build_extras.py previews       before `hyperctl build`
      data/link_previews.json: the preview card under each post with an external link (title,
      description and image from the linked page's Open Graph tags). Read by data/blog/posts.js.

  tools/build_extras.py extras public  after `hyperctl build`, on the build output
      /blog/feed.xml (RSS) and /blog/feed.json, which keep the Micro.blog `guid`s so readers
      don't show old posts again; /blog/archive/index.json and /blog/photos/index.json
      (Micro.blog-style JSON); Markdown copies of the main pages (front matter `markdown:`);
      /llms.txt; /sitemap.xml; /.well-known/about.md (AboutSpec) and /.well-known/contact.vcf
      (ContactSpec) from the home page; and the 1200x630 link-preview cards (/og/...png) that pages
      without a photo point to (plugins/og_image.js).

Page data comes from HyperTemplates itself (`hyperctl cms data inspect`), so posts, dates and
rendered HTML are exactly what the layouts used. Needs Pillow for the cards.
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.parse
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from crosspost import link_preview  # noqa: E402  (same Open Graph reader as the Bluesky cards)

HYPERCTL = os.environ.get("HYPERCTL", "hyperctl")
CONTENT = pathlib.Path("content")
OG = pathlib.Path(__file__).parent / "og"
FEED_LIMIT = 25


def inspect(keypath):
    out = subprocess.run([HYPERCTL, "cms", "data", "inspect", keypath], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def rfc3339(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def absolute(base, html_text):
    """Root-relative src/href -> absolute, for feeds read outside the site."""
    return re.sub(r'(\s(?:src|href)=")/(?!/)', rf"\1{base}/", html_text)


def source_file(path):
    """/blog/2026/06/04/hello.html or /blog/hello/ -> its content/.../index.md"""
    stem = path[:-len(".html")] if path.endswith(".html") else path.rstrip("/")
    for name in ("index.md", "page.md"):
        f = CONTENT / stem.lstrip("/") / name
        if f.is_file():
            return f
    return None


def raw_markdown(path):
    f = source_file(path)
    if not f:
        return ""
    return re.sub(r"^---\n.*?\n---\n?", "", f.read_text(encoding="utf-8"), count=1, flags=re.S)


def plain(html_text):
    text = re.sub(r"<br\s*/?>|</(p|li|h[1-6]|blockquote|div)>", " ", html_text or "")
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", text))).strip()


def truncate(text, limit):
    """Same rule as plugins/excerpt.js (Hugo's truncate): whole words, then " …"."""
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut[:-1]) + " …"


def write(root, rel, text):
    f = root / rel.lstrip("/")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text, encoding="utf-8")
    print(f"wrote {f}")


# ---------------------------------------------------------------- previews

def first_external_link(html_text, site_host):
    """The link a post's preview card shows: external, not an @mention, not this site."""
    for m in re.finditer(r"<a(\s[^>]*)>(.*?)</a>", html_text or "", re.S):
        attrs, text = m.group(1), plain(m.group(2))
        href = re.search(r'\shref="([^"]*)"', attrs)
        if not href or "data-hyper-mention" in attrs or text.startswith("@"):
            continue
        url = html.unescape(href.group(1))
        host = urllib.parse.urlsplit(url).netloc.removeprefix("www.")
        if url.startswith("http") and host and host != site_host:
            return url
    return None


def previews():
    site_host = urllib.parse.urlsplit(inspect("site.base_url")).netloc.removeprefix("www.")
    cards = {}
    for post in inspect("data.blog.posts"):
        url = first_external_link(post.get("content"), site_host)
        if not url:
            continue
        try:
            info = link_preview(url)
        except Exception as e:  # a dead link just means no card
            print(f"link preview: {url}: {e}")
            continue
        if not info["title"] or info["title"] == url:
            continue
        cards[post["path"]] = {
            "url": url,
            "host": urllib.parse.urlsplit(url).netloc.removeprefix("www."),
            "title": info["title"],
            "description": info["description"],
            "image": info["image"],
        }
    pathlib.Path("data/link_previews.json").write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote data/link_previews.json ({len(cards)} cards)")


# ---------------------------------------------------------------- feeds

def rss(site, posts):
    base, blog = site["base_url"].rstrip("/"), site["base_url"].rstrip("/") + "/blog/"
    fmt = "%a, %d %b %Y %H:%M:%S %z"
    items = []
    for p in posts[:FEED_LIMIT]:
        items.append(f"""    <item>
      <title>{escape(p.get("title") or "")}</title>
      <link>{escape(p["canonical_url"])}</link>
      <pubDate>{rfc3339(p["created_at"]).strftime(fmt)}</pubDate>
      <guid>{escape(p.get("guid") or p["canonical_url"])}</guid>
      <description>{escape(absolute(base, p["body"]))}</description>
      <source:markdown>{escape(absolute(base, raw_markdown(p["path"])))}</source:markdown>
    </item>""")
    updated = rfc3339(posts[0]["created_at"]).strftime(fmt) if posts else ""
    return f"""<rss xmlns:source="http://source.scripting.com/" version="2.0">
  <channel>
    <title>{escape(site["blog"]["title"])}</title>
    <link>{blog}</link>
    <description></description>
    <language>en</language>
    <lastBuildDate>{updated}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>
"""


def json_feed(site, items, feed_path):
    base = site["base_url"].rstrip("/")
    return json.dumps({
        "version": "https://jsonfeed.org/version/1",
        "title": site["blog"]["title"],
        "icon": base + site["author"]["avatar"],
        "home_page_url": base + "/blog/",
        "feed_url": base + feed_path,
        "items": items,
    }, indent=2, ensure_ascii=False) + "\n"


def feeds(root, site, posts):
    base = site["base_url"].rstrip("/")
    write(root, "/blog/feed.xml", rss(site, posts))

    items = []
    for p in posts[:FEED_LIMIT]:
        item = {"id": p.get("guid") or p["canonical_url"]}
        if p.get("title"):
            item["title"] = p["title"]
        item["content_html"] = absolute(base, p["body"])
        if p.get("summary"):
            item["summary"] = plain(p["summary"])
        item["date_published"] = p["created_at"]
        item["url"] = p["canonical_url"]
        items.append(item)
    write(root, "/blog/feed.json", json_feed(site, items, "/blog/feed.json"))

    archive = [{"id": p["canonical_url"], "title": p.get("title") or "",
                "content_text": truncate(plain(p.get("summary") or p["body"]), 100),
                "date_published": p["created_at"], "url": p["canonical_url"]} for p in posts]
    write(root, "/blog/archive/index.json", json_feed(site, archive, "/blog/archive/index.json"))

    photos = [{"id": p["canonical_url"], "title": p.get("title") or "", "content_html": absolute(base, p["body"]),
               "date_published": p["created_at"], "url": p["canonical_url"],
               "image": p["image"] if p["image"].startswith("http") else base + p["image"]}
              for p in posts if p.get("image")]
    write(root, "/blog/photos/index.json", json_feed(site, photos, "/blog/photos/index.json"))


# ---------------------------------------------------------------- Markdown copies, llms.txt, sitemap

def updated_line(page):
    return f"---\n\nUpdated {(page.get('updated_at') or page['created_at'])[:10]}.\n"


def bare_url(url):
    return re.sub(r"^https?://", "", url).rstrip("/")


def profile(site, page, by_path, markdown_links):
    """The home page as Markdown (bio, links, elsewhere), for /index.md and /.well-known/about.md.
    Site pages link to their Markdown copy when markdown_links, else to the HTML page."""
    base = site["base_url"].rstrip("/")
    lines = [page["bio"], "", "## Links", ""]
    for link in page.get("links", []):
        target = by_path.get(link["url"], {})
        if markdown_links and target.get("markdown"):
            url = base + target["markdown"]
        else:
            url = base + link["url"] if link["url"].startswith("/") else link["url"]
        feeds = f" ([RSS]({base}/blog/feed.xml), [JSON Feed]({base}/blog/feed.json))" if link.get("feeds") else ""
        lines.append(f"- [{link['name']}]({url}){feeds}")
    lines += ["", "## Elsewhere", ""]
    lines += [f"- [{e['name']}]({e['url']})" for e in page.get("elsewhere", [])]
    lines += ["", "---", "", "He/They · 🏳️‍🌈 · Bogotá, Colombia", ""]
    return "\n".join(lines)


def md_home(site, page, by_path):
    return f"# {site['title']}\n\n" + profile(site, page, by_path, markdown_links=True)


def about_spec(site, page, by_path):
    """AboutSpec (https://aboutspec.org/): the bio as `summary`, then the profile linking to HTML pages."""
    summary = json.dumps(page["bio"], ensure_ascii=False)  # a valid YAML double-quoted string
    return f"---\nsummary: {summary}\n---\n\n" + profile(site, page, by_path, markdown_links=False)


def contact_spec(site, page):
    """ContactSpec (https://contactspec.org/): a vCard 4.0 (RFC 6350) with the name (site title), email
    (the mailto: link in `elsewhere`), home page, photo, and the other `elsewhere` links as social
    profiles (RFC 9554). Lines end in CRLF and fold at 75 characters; text escapes \\ , ; ."""
    def esc(s):
        return re.sub(r"([\\,;])", r"\\\1", s)
    given, _, family = site["title"].partition(" ")
    base = site["base_url"].rstrip("/")
    elsewhere = page.get("elsewhere", [])
    lines = ["BEGIN:VCARD", "VERSION:4.0", "KIND:individual", f"FN:{esc(site['title'])}", f"N:{esc(family)};{esc(given)};;;"]
    lines += [f"EMAIL;PREF=1:{e['url'].removeprefix('mailto:')}" for e in elsewhere if e["url"].startswith("mailto:")]
    lines += [f"URL:{base}/", f"PHOTO:{base}/images/profile.png"]
    lines += [f'SOCIALPROFILE;SERVICE-TYPE="{e["name"]}":{e["url"]}' for e in elsewhere if not e["url"].startswith("mailto:")]
    lines.append("END:VCARD")
    folded = []
    for line in lines:  # the first 75 characters, then continuation lines of a space + 74
        folded.append(line[:75])
        folded += [" " + line[i:i + 74] for i in range(75, len(line), 74)]
    return "\r\n".join(folded) + "\r\n"


def well_known(root, site, pages):
    by_path = {p["path"]: p for p in pages}
    home = by_path["/"]
    write(root, "/.well-known/about.md", about_spec(site, home, by_path))
    out = root / ".well-known/contact.vcf"
    out.write_bytes(contact_spec(site, home).encode("utf-8"))  # keep the CRLFs exactly
    print(f"wrote {out}")


def md_now(site, page):
    return (f"# {page['title']}\n\n{page['note']}\n\n"
            "This is a [now page](https://nownownow.com/about), and if you have your own site, you should make one too.\n\n"
            f"{raw_markdown(page['path']).strip()}\n\n{updated_line(page)}")


def md_resume(site, page):
    base = site["base_url"].rstrip("/")
    out = [f"# {page['title']}", "", page["note"], "", page["summary"], "", f"[Download PDF]({base}/resume.pdf)", "", "## Work Experience", ""]
    for role in page["roles"]:
        out += [f"### {role['title']}", ""] + [f"- {i}" for i in role["items"]] + [""]
    def table(rows):
        return ["| | |", "|---|---|"] + [f"| {r['name']} | {r['value']} |" for r in rows]
    out += ["## Skills", ""] + table(page["skills"]) + ["", "## Education & Training", ""]
    out += [f"- {i}" for i in page["education"]] + ["", "## Languages", ""]
    out += [f"- {i}" for i in page["languages"]] + ["", "## About", ""] + table(page["about"])
    out += ["", "## Portfolio", ""]
    out += [f"- {p['name']}" + (f" — [{bare_url(p['url'])}]({p['url']})" if p.get("url") else "") for p in page["portfolio"]]
    return "\n".join(out) + "\n"


def md_blogroll(site, page):
    base = site["base_url"].rstrip("/")
    feeds = inspect("data.blogroll")["body"]["outlines"]
    roll = "\n".join(f"- [{f['title']}]({f['htmlUrl']}) · [feed]({f['xmlUrl']})" for f in feeds)
    return (f"# {page['title']}\n\n{page['note']}\n\n"
            f"Inspired by old-school blogrolls. You can subscribe to this same list via [OPML export]({base}{page['opml']}).\n\n"
            f"## Roll\n\n{roll}\n\n{updated_line(page)}")


MARKDOWN = {"home": md_home, "now": md_now, "resume": md_resume, "blogroll": md_blogroll}


def markdown_copies(root, site, pages):
    by_path = {p["path"]: p for p in pages}
    for page in pages:
        render = MARKDOWN.get(page.get("layout"))
        if page.get("markdown") and render:
            text = render(site, page, by_path) if render is md_home else render(site, page)
            write(root, page["markdown"], text)


def llms(root, site, pages):
    base = site["base_url"].rstrip("/")
    by_path = {p["path"]: p for p in pages}
    home = by_path["/"]
    bio = re.sub(r"[^\u0020-\u024F\u2010-\u205E]", "", home["bio"])
    bio = re.sub(r" ([,.;:!?])", r"\1", re.sub(r"\s+", " ", bio)).strip()
    lines = [f"# {site['title']}", "", f"> {bio}", "",
             "Personal website. Every page has a Markdown version at the same path with a `.md` extension.", "",
             "## Pages", "", f"- [Home]({base}{home['markdown']}): Bio and links."]
    for item in site["nav"]:
        page = by_path.get(item["url"])
        if page and page["path"] != "/" and page.get("markdown"):
            lines.append(f"- [{page['title']}]({base}{page['markdown']}): {page.get('llms', '')}")
    blogroll = next((p for p in pages if p.get("opml")), None)
    lines += ["", "## Blog", "", f"- [{site['blog']['title']}]({base}/blog/)", f"- [RSS feed]({base}/blog/feed.xml)",
              f"- [JSON Feed]({base}/blog/feed.json)", "", "## Optional", "", f"- [Resume PDF]({base}/resume.pdf)"]
    if blogroll:
        lines.append(f"- [Blogroll OPML]({base}{blogroll['opml']})")
    lines.append(f"- [human.json]({base}/human.json): Sites I vouch for.")
    write(root, "/llms.txt", "\n".join(lines) + "\n")


def sitemap(root, site, pages):
    urls = []
    for p in sorted(pages, key=lambda p: rfc3339(p.get("updated_at") or p["created_at"]), reverse=True):
        if p.get("layout") == "notfound":
            continue
        lastmod = rfc3339(p.get("updated_at") or p["created_at"]).isoformat()
        urls.append(f"  <url>\n    <loc>{escape(p['canonical_url'])}</loc>\n    <lastmod>{lastmod}</lastmod>\n  </url>")
    write(root, "/sitemap.xml", '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


# ---------------------------------------------------------------- link-preview cards

def card_text(site, page, path, og_title):
    """Breadcrumb and body text for a page's card (pages without their own photo)."""
    blog = path.startswith("/blog/")
    if path == "/":
        return site["title"], page.get("bio", ""), False
    crumb = f"{site['title']} / {'Blog' if blog else (page or {}).get('title') or og_title}"
    if page is None:  # generated pages (tags): their title
        return crumb, og_title, False
    if page.get("layout") == "post":
        return crumb, page.get("title") or plain(page.get("summary") or page.get("content")), bool(page.get("title"))
    return crumb, page.get("note") or page.get("description") or page.get("title") or "", False


def wrap(text, max_chars):
    lines, line = [], ""
    for word in text.split(" "):
        attempt = word if not line else f"{line} {word}"
        if len(attempt) <= max_chars:
            line = attempt
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def card_lines(text, max_chars, max_lines=4):
    # The font has no emoji: keep Latin text and common punctuation only.
    text = re.sub(r"[^\u0020-\u024F\u2010-\u2027\u2030-\u205E\u20AC]", "", text)
    text = re.sub(r" ([,.;:!?])", r"\1", re.sub(r"\s+", " ", text)).strip()
    lines = wrap(text, max_chars)
    # Too long? Drop whole trailing sentences if the rest still fills 3+ lines; else cut with "…".
    if len(lines) > max_lines:
        sentences = re.findall(r"[^.!?]+[.!?]+", text)
        for keep in range(len(sentences) - 1, 0, -1):
            shorter = wrap("".join(sentences[:keep]).strip(), max_chars)
            if max_lines - 1 <= len(shorter) <= max_lines:
                lines = shorter
                break
    if len(lines) > max_lines:
        last = lines[max_lines - 1][: max_chars - 1].rstrip(" .,;:") + "…"
        lines = lines[: max_lines - 1] + [last]
    return lines


def draw_card(out, crumb, text, bold, domain):
    from PIL import Image, ImageDraw, ImageFont

    size = 56 if bold else 46
    lines = card_lines(text, int(1056 / (size * 0.6)))
    regular, heavy = OG / "fonts/JetBrainsMono-Regular.ttf", OG / "fonts/JetBrainsMono-Bold.ttf"
    with Image.open(OG / "base.png") as base:
        img = base.convert("RGBA")
    d = ImageDraw.Draw(img)
    d.text((224, 100), crumb, font=ImageFont.truetype(str(heavy), 40), fill="#000000")
    body = ImageFont.truetype(str(heavy if bold else regular), size)
    d.multiline_text((72, 232), "\n".join(lines), font=body, fill="#000000", spacing=16 if bold else 14)
    d.text((72, 548), domain, font=ImageFont.truetype(str(regular), 30), fill="#6b6b6b")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, "PNG", optimize=True)


def cards(root, site, pages):
    """Draw every /og/…png card that a built page points to and that doesn't exist yet."""
    base = site["base_url"].rstrip("/")
    by_path = {p["path"]: p for p in pages}
    drawn = 0
    for f in sorted(root.rglob("*.html")):
        doc = f.read_text(encoding="utf-8")
        m = re.search(r'<meta property="og:image" content="' + re.escape(base) + r'(/og/[^"]+\.png)"', doc)
        if not m or (root / m.group(1).lstrip("/")).exists():
            continue
        rel = "/" + f.relative_to(root).as_posix()
        path = rel[: -len("index.html")] if rel.endswith("/index.html") else rel
        title = re.search(r'<meta property="og:title" content="([^"]*)"', doc)
        og_title = html.unescape(title.group(1)).removesuffix(f" · {site['title']}") if title else ""
        crumb, text, bold = card_text(site, by_path.get(path), path, og_title)
        draw_card(root / m.group(1).lstrip("/"), crumb, text, bold, bare_url(base))
        drawn += 1
    print(f"drew {drawn} link-preview cards")


def extras(root):
    root = pathlib.Path(root)
    site = inspect("site")
    pages = [p for p in site.pop("pages") if not p.get("draft")]
    posts = inspect("data.blog.posts")
    feeds(root, site, posts)
    markdown_copies(root, site, pages)
    well_known(root, site, pages)
    llms(root, site, pages)
    sitemap(root, site, pages)
    cards(root, site, pages)


if __name__ == "__main__":
    if sys.argv[1:2] == ["previews"]:
        previews()
    elif sys.argv[1:2] == ["extras"] and len(sys.argv) == 3:
        extras(sys.argv[2])
    else:
        sys.exit(__doc__)
