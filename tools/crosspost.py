#!/usr/bin/env python3
"""Cross-post new blog posts to Bluesky and Mastodon, then record the copies in front matter.

Run by .github/workflows/crosspost.yaml after a push to main. For each post in
content/blog/ dated on or after CROSSPOST_SINCE that has no `bluesky:` (or `mastodon:`)
block yet, it posts to that network and writes the block back in the same shape
Micro.blog used, so the comments box under the post can find its replies.

Environment:
  BLUESKY_HANDLE, BLUESKY_APP_PASSWORD   Bluesky account + app password
  MASTODON_INSTANCE, MASTODON_TOKEN      e.g. social.lol + access token (write:statuses, write:media)
  SITE_URL                               https://juanvisbal.com
  DRY_RUN=1                              print what would be posted; change nothing
  CHECK_LOGIN=1                          only log in to both networks and print the accounts

Text rules: Mastodon gets the full post (social.lol allows 10,000 characters). Bluesky
gets the full text if it fits in 300 characters; otherwise a shortened version plus the
link. Titled posts get "Title + link" on both. Up to 4 images are attached, with alt text.
"""
import datetime as dt
import io
import json
import os
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import uuid

CONTENT = pathlib.Path("content/blog")
STATIC = pathlib.Path("static")
CROSSPOST_SINCE = dt.date(2026, 10, 1)  # imported Micro.blog posts (newest: 2026-09-22) were already cross-posted
BLUESKY_LIMIT = 300
BLUESKY_IMAGE_MAX = 950_000  # Bluesky's limit is 1,000,000 bytes per image
MAX_IMAGES = 4
DRY_RUN = os.environ.get("DRY_RUN") == "1"


# ---------------------------------------------------------------- HTTP helpers

def request(method, url, *, headers=None, data=None, json_body=None, timeout=60):
    headers = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')[:500]}") from None


def multipart(fields, files):
    boundary = uuid.uuid4().hex
    out = io.BytesIO()
    for name, value in fields.items():
        out.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, (filename, content, ctype) in files.items():
        out.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                  f"Content-Type: {ctype}\r\n\r\n".encode())
        out.write(content)
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={boundary}"


# ---------------------------------------------------------------- Posts

class Post:
    def __init__(self, path):
        self.path = path
        raw = path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
        if not m:
            raise ValueError(f"{path}: no front matter")
        self.front, self.body = m.group(1), m.group(2)

    def field(self, key):
        m = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', self.front, re.M)
        return m.group(1) if m else None

    def has_block(self, key):
        return re.search(rf"^{key}:\s*$", self.front, re.M) is not None

    @property
    def date(self):
        return dt.datetime.fromisoformat(self.field("date").replace("Z", "+00:00"))

    @property
    def title(self):
        return self.field("title") or ""

    def permalink(self, site):
        url = self.field("url")
        if not url:  # same rule as archetypes/blog.md
            rel = self.path.relative_to("content").with_suffix(".html")
            url = "/" + rel.as_posix()
        return site.rstrip("/") + url.removesuffix(".html")

    def images(self):
        found = []
        for m in re.finditer(r'<img\s[^>]*src="([^"]+)"[^>]*>', self.body):
            alt = re.search(r'alt="([^"]*)"', m.group(0))
            found.append((m.group(1), alt.group(1) if alt else ""))
        for m in re.finditer(r"!\[([^\]]*)\]\(([^)\s]+)", self.body):
            found.append((m.group(2), m.group(1)))
        out = []
        for src, alt in found:
            if src.startswith("/"):
                local = STATIC / src.lstrip("/")
                if local.is_file():
                    out.append((local, alt))
        return out[:MAX_IMAGES]

    def add_block(self, text):
        raw = self.path.read_text(encoding="utf-8")
        # insert before the closing --- of the front matter
        m = re.match(r"^(---\n.*?\n)(---\n?)", raw, re.S)
        new = m.group(1) + text.rstrip("\n") + "\n" + raw[len(m.group(1)):]
        self.path.write_text(new, encoding="utf-8")
        self.__init__(self.path)


def to_segments(markdown):
    """Markdown body -> list of (text, link) segments; images and HTML tags removed."""
    s = re.sub(r"<img\s[^>]*>", "", markdown)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", s)
    s = re.sub(r"\n{3,}", "\n\n", s).strip()
    segments, pos = [], 0
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", s):
        segments.append((s[pos:m.start()], None))
        segments.append((m.group(1), m.group(2)))
        pos = m.end()
    segments.append((s[pos:], None))
    return [(t, l) for t, l in segments if t]


def graphemes(text):
    # Close enough for the 300 limit: count code points minus combining marks / variation selectors / ZWJ.
    return sum(1 for ch in text if not (unicodedata.combining(ch) or ch in "‍︎️"))


# ---------------------------------------------------------------- Bluesky

class Bluesky:
    def __init__(self, handle, password):
        did = request("GET", f"https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle={handle}")[1]["did"]
        doc = request("GET", f"https://plc.directory/{did}")[1]
        self.pds = next(s["serviceEndpoint"] for s in doc["service"] if s["id"] == "#atproto_pds")
        session = request("POST", f"{self.pds}/xrpc/com.atproto.server.createSession",
                          json_body={"identifier": handle, "password": password})[1]
        self.did, self.handle, self.jwt = session["did"], session["handle"], session["accessJwt"]

    def upload(self, path, alt):
        data, ctype, size = shrink(path, BLUESKY_IMAGE_MAX)
        blob = request("POST", f"{self.pds}/xrpc/com.atproto.repo.uploadBlob",
                       headers={"Authorization": f"Bearer {self.jwt}", "Content-Type": ctype}, data=data)[1]["blob"]
        return {"alt": alt, "image": blob, "aspectRatio": {"width": size[0], "height": size[1]}}

    def post(self, post, site):
        link = post.permalink(site)
        segments, text_len = to_segments(post.body), None
        if post.title:
            segments = [(post.title + "\n\n", None), (link, link)]
        else:
            text_len = graphemes("".join(t for t, _ in segments))
            if text_len > BLUESKY_LIMIT:
                budget = BLUESKY_LIMIT - graphemes(link) - 3
                kept, used = [], 0
                for t, l in segments:
                    room = budget - used
                    if room <= 0:
                        break
                    if graphemes(t) > room:
                        t = t[:room].rsplit(" ", 1)[0] if " " in t[:room] else t[:room]
                        kept.append((t.rstrip() + "…", l))
                        break
                    kept.append((t, l))
                    used += graphemes(t)
                segments = kept + [("\n\n", None), (link, link)]

        text, facets, byte = "", [], 0
        for t, l in segments:
            b = t.encode()
            if l:
                facets.append({"index": {"byteStart": byte, "byteEnd": byte + len(b)},
                               "features": [{"$type": "app.bsky.richtext.facet#link", "uri": l}]})
            text += t
            byte += len(b)

        record = {"$type": "app.bsky.feed.post", "text": text, "facets": facets, "langs": ["en"],
                  "createdAt": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")}
        images = post.images()
        if DRY_RUN:
            print(f"  Bluesky ({graphemes(text)} chars, {len(images)} images):\n    " + text.replace("\n", "\n    "))
            return None
        if images:
            record["embed"] = {"$type": "app.bsky.embed.images", "images": [self.upload(p, a) for p, a in images]}
        res = request("POST", f"{self.pds}/xrpc/com.atproto.repo.createRecord",
                      headers={"Authorization": f"Bearer {self.jwt}"},
                      json_body={"repo": self.did, "collection": "app.bsky.feed.post", "record": record})[1]
        rkey = res["uri"].rsplit("/", 1)[1]
        return (f'bluesky:\n  id: "{res["cid"]}"\n  url: "{res["uri"]}"\n'
                f'  link: "https://bsky.app/profile/{self.did}/post/{rkey}"\n  handle: "{self.handle}"\n'
                f'  hostname: "bsky.social"\n  did: "{self.did}"\n')


# ---------------------------------------------------------------- Mastodon

class Mastodon:
    def __init__(self, instance, token):
        self.base, self.auth = f"https://{instance}", {"Authorization": f"Bearer {token}"}
        self.instance = instance
        me = request("GET", f"{self.base}/api/v1/accounts/verify_credentials", headers=self.auth)[1]
        self.username = me["username"]

    def upload(self, path, alt):
        data, ctype, _ = shrink(path, 8_000_000)
        body, mp_type = multipart({"description": alt}, {"file": (path.name, data, ctype)})
        status, media = request("POST", f"{self.base}/api/v2/media",
                                headers={**self.auth, "Content-Type": mp_type}, data=body, timeout=120)
        for _ in range(30):  # 202 = still processing
            if status == 200 and media.get("url"):
                break
            time.sleep(2)
            status, media = request("GET", f"{self.base}/api/v1/media/{media['id']}", headers=self.auth)
        return media["id"]

    def post(self, post, site):
        link = post.permalink(site)
        if post.title:
            text = f"{post.title}\n\n{link}"
        else:
            text = "".join(t if not l or t == l else f"{t} ({l})" for t, l in to_segments(post.body))
        images = post.images()
        if DRY_RUN:
            print(f"  Mastodon ({len(text)} chars, {len(images)} images):\n    " + text.replace("\n", "\n    "))
            return None
        body = {"status": text, "visibility": "public", "language": "en",
                "media_ids": [self.upload(p, a) for p, a in images]}
        res = request("POST", f"{self.base}/api/v1/statuses",
                      headers={**self.auth, "Idempotency-Key": f"{post.path}"}, json_body=body)[1]
        return f'mastodon:\n  id: "{res["id"]}"\n  username: "{self.username}"\n  hostname: "{self.instance}"\n'


# ---------------------------------------------------------------- Images

def shrink(path, max_bytes):
    """Return (bytes, content type, (w, h)), re-encoding as JPEG if the file is too big."""
    from PIL import Image, ImageOps

    raw = path.read_bytes()
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        size = im.size
        if len(raw) <= max_bytes and im.format in ("JPEG", "PNG", "GIF", "WEBP"):
            return raw, Image.MIME[im.format], size
        im = im.convert("RGB")
        for edge in (2000, 1600, 1200, 1000):
            copy = im.copy()
            copy.thumbnail((edge, edge))
            for quality in (85, 75, 65):
                buf = io.BytesIO()
                copy.save(buf, "JPEG", quality=quality, optimize=True)
                if buf.tell() <= max_bytes:
                    return buf.getvalue(), "image/jpeg", copy.size
    raise RuntimeError(f"{path}: could not shrink below {max_bytes} bytes")


# ---------------------------------------------------------------- Main

def wait_until_live(url, minutes=10):
    for _ in range(minutes * 4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as r:
                if r.status == 200:
                    return
        except urllib.error.HTTPError:
            pass
        time.sleep(15)
    raise RuntimeError(f"{url} is not live yet")


def main():
    site = os.environ.get("SITE_URL", "https://juanvisbal.com")
    if os.environ.get("CHECK_LOGIN") == "1":
        bsky = Bluesky(os.environ["BLUESKY_HANDLE"], os.environ["BLUESKY_APP_PASSWORD"])
        masto = Mastodon(os.environ["MASTODON_INSTANCE"], os.environ["MASTODON_TOKEN"])
        print(f"Bluesky: logged in as {bsky.handle} ({bsky.did}) via {bsky.pds}")
        print(f"Mastodon: logged in as @{masto.username}@{masto.instance}")
        return
    now = dt.datetime.now(dt.timezone.utc)
    pending = []
    for path in sorted(CONTENT.glob("[0-9][0-9][0-9][0-9]/**/*.md")):
        post = Post(path)
        if post.field("draft") == "true" or post.date.date() < CROSSPOST_SINCE or post.date > now:
            continue
        if not post.has_block("bluesky") or not post.has_block("mastodon"):
            pending.append(post)
    if not pending:
        print("Nothing to cross-post.")
        return

    if DRY_RUN:  # no logins; post() prints and returns before using the session
        bsky, masto = object.__new__(Bluesky), object.__new__(Mastodon)
    else:
        bsky = Bluesky(os.environ["BLUESKY_HANDLE"], os.environ["BLUESKY_APP_PASSWORD"])
        masto = Mastodon(os.environ["MASTODON_INSTANCE"], os.environ["MASTODON_TOKEN"])

    failures = 0
    for post in pending:
        print(f"{post.path} -> {post.permalink(site)}")
        if not DRY_RUN:
            wait_until_live(post.permalink(site))
        for key, client in (("bluesky", bsky), ("mastodon", masto)):
            if post.has_block(key):
                continue
            try:
                block = client.post(post, site)
                if block:
                    post.add_block(block)
                    print(f"  posted to {key}")
            except Exception as e:  # keep going with the other network / posts
                failures += 1
                print(f"  {key} failed: {e}", file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
