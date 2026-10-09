#!/usr/bin/env python3
"""One-off cleanup of the Micro.blog Hugo export (run 2026-10-08).

Usage: tools/import_microblog.py content/2026

- Image paths: relative `uploads/...`, `cdn.uploads.micro.blog/<site>/...` and
  `blog.juanvisbal.com/uploads/...` all become `/uploads/...` (files in static/uploads).
- Drops Micro.blog-only front matter: `microblog`, `thumbnail`, `opengraph`
  (Micro.blog-generated cards on S3).
- Keeps `guid` (feed item IDs stay the same, so readers don't show duplicates),
  `url` (permalinks unchanged) and the bluesky/mastodon/linkedin syndication data.

Idempotent: running it twice changes nothing the second time.
"""
import pathlib
import re
import sys

URL_FIXES = [
    (re.compile(r'src="uploads/'), 'src="/uploads/'),
    (re.compile(r"https://cdn\.uploads\.micro\.blog/\d+/"), "/uploads/"),
    (re.compile(r"https://blog\.juanvisbal\.com/uploads/"), "/uploads/"),
]
DROP_KEYS = {"microblog", "thumbnail", "opengraph"}


def clean_front_matter(fm: str) -> str:
    out, skipping = [], False
    for line in fm.splitlines():
        key = re.match(r"^([A-Za-z_]+):", line)
        if key:
            skipping = key.group(1) in DROP_KEYS
        elif not line.startswith((" ", "-")):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out)


def convert(text: str) -> str:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("no YAML front matter")
    text = "---\n" + clean_front_matter(m.group(1)) + "\n---\n" + text[m.end():]
    for pattern, repl in URL_FIXES:
        text = pattern.sub(repl, text)
    return text


def main(root: str) -> None:
    for path in sorted(pathlib.Path(root).rglob("*.md")):
        old = path.read_text(encoding="utf-8")
        new = convert(old)
        if new != old:
            path.write_text(new, encoding="utf-8")
            print(f"updated {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "content/2026")
