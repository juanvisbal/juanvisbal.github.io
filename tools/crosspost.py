#!/usr/bin/env python3
"""Cross-post new blog posts to Bluesky, Mastodon and /dev/null; record copies in front matter.

Run by .github/workflows/crosspost.yaml after a push to main. Each eligible post
without a network's front matter block is posted there, then the block is saved.
Bluesky and Mastodon use Micro.blog's shape so the comments box can find replies.
/dev/null is opt-in and starts at DEVNULL_SINCE, without backfilling older posts.

Environment:
  BLUESKY_HANDLE, BLUESKY_APP_PASSWORD   Bluesky account + app password
  MASTODON_INSTANCE, MASTODON_TOKEN      e.g. social.lol + access token (write:statuses, write:media)
  DEVNULL_PUBLIC_KEY                     path to an Ed25519/RSA public key loaded in ssh-agent;
                                         enables /dev/null (account + key must be on GitHub)
  SITE_URL                               https://juanvisbal.com
  DRY_RUN=1                              preview all networks without logging in or writing files
  CHECK_LOGIN=1                          only check configured logins/signing; post nothing
  BLUESKY_DELETE="at://… at://…"         delete these Bluesky posts (yours only) before posting,
                                         e.g. to re-post them with a link card

Text rules: Mastodon gets the full post (social.lol allows 10,000 characters). Bluesky
gets the full text if it fits in 300 characters; otherwise a shortened version plus the
link. Titled posts get "Title + link" on all networks. Up to 4 images are attached,
with alt text. /dev/null gets at most 3 images (its CLI has no alt-text field), and
text over its 4,000-character limit is shortened with a link.
"""
import datetime as dt
import hashlib
import html
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

CONTENT = pathlib.Path("content/blog")
STATIC = pathlib.Path("static")
CROSSPOST_SINCE = dt.date(2026, 10, 1)  # imported Micro.blog posts (newest: 2026-09-22) were already cross-posted
DEVNULL_SINCE = dt.date(2026, 10, 21)  # new network: don't backfill the existing blog
DEVNULL_LIMIT = 4000
DEVNULL_IMAGE_MAX = 10_240_000
BLUESKY_LIMIT = 300
BLUESKY_IMAGE_MAX = 950_000  # Bluesky's limit is 1,000,000 bytes per image
MAX_IMAGES = 4
DRY_RUN = os.environ.get("DRY_RUN") == "1"
# Cloudflare answers 403 to Python's default User-Agent, so always send our own.
USER_AGENT = "juanvisbal-crosspost/1.0 (+https://juanvisbal.com/blog/)"


# ---------------------------------------------------------------- HTTP helpers

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(method, url, *, headers=None, data=None, json_body=None, timeout=60,
            text_response=False, follow_redirects=True):
    headers = {"User-Agent": USER_AGENT, **(headers or {})}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    open_url = urllib.request.urlopen if follow_redirects else urllib.request.build_opener(NoRedirect()).open
    for attempt in range(1, 5):
        try:
            with open_url(req, timeout=timeout) as r:
                body = r.read()
                if text_response:
                    return r.status, body.decode("utf-8")
                return r.status, (json.loads(body) if body else {})
        except urllib.error.HTTPError as e:
            with e:
                raise RuntimeError(f"{method} {url} -> {e.code}: {e.read().decode(errors='replace')[:500]}") from None
        except urllib.error.URLError as e:
            # Retry only if the connection itself failed (e.g. "Network is unreachable"):
            # the request never reached the server, so retrying can't post twice.
            # A timeout on a non-GET might have been delivered, so don't retry that.
            timed_out = isinstance(e.reason, TimeoutError)
            if attempt == 4 or (timed_out and method != "GET"):
                raise
            print(f"  network error ({e.reason}); retrying in {attempt * 10}s")
            time.sleep(attempt * 10)


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
        m = re.search(rf"^{key}:\s*(.*?)\s*$", self.front, re.M)
        if not m:
            return None
        value = m.group(1)
        if len(value) >= 2 and value[0] == value[-1] == '"':
            try:  # YAML double-quoted strings use JSON-style escapes (\" and \\)
                return json.loads(value)
            except ValueError:
                return value[1:-1]
        if len(value) >= 2 and value[0] == value[-1] == "'":
            return value[1:-1].replace("''", "'")
        return value

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
    # Bare URLs become links too (Bluesky only makes text clickable via facets).
    out = []
    for t, l in segments:
        if l:
            out.append((t, l))
            continue
        last = 0
        for m in re.finditer(r"https?://[^\s<>()]+[^\s<>().,;:!?'\"]", t):
            out.append((t[last:m.start()], None))
            out.append((m.group(0), m.group(0)))
            last = m.end()
        out.append((t[last:], None))
    return [(t, l) for t, l in out if t]


def post_text(post, site):
    """Full plain text with link destinations preserved; titled posts advertise the original."""
    if post.title:
        return f"{post.title}\n\n{post.permalink(site)}"
    return "".join(t if not l or t == l else f"{t} ({l})" for t, l in to_segments(post.body))


def graphemes(text):
    # Close enough for the 300 limit: count code points minus combining marks / variation selectors / ZWJ.
    return sum(1 for ch in text if not (unicodedata.combining(ch) or ch in "‍︎️"))


# ---------------------------------------------------------------- Link cards

def link_preview(url):
    """Title, description and image URL from a page's Open Graph / <title> / description tags."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=20) as r:
        page = r.read(600_000).decode(r.headers.get_content_charset() or "utf-8", errors="replace")
        final_url = r.geturl()

    def meta(*names):
        for name in names:
            for pattern in (rf'<meta[^>]+(?:property|name)=["\']{name}["\'][^>]*content=["\']([^"\']*)',
                            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{name}["\']'):
                m = re.search(pattern, page, re.I)
                if m and m.group(1).strip():
                    return html.unescape(m.group(1).strip())
        return ""

    title = meta("og:title", "twitter:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
        title = html.unescape(m.group(1).strip()) if m else url
    image = meta("og:image", "twitter:image")
    return {
        "title": title[:300],
        "description": meta("og:description", "description", "twitter:description")[:1000],
        "image": urllib.parse.urljoin(final_url, image) if image else "",
    }


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

    def delete(self, at_uri):
        m = re.match(r"^at://([^/]+)/app\.bsky\.feed\.post/([A-Za-z0-9]+)$", at_uri)
        if not m or m.group(1) != self.did:
            raise RuntimeError(f"not one of your posts: {at_uri}")
        request("POST", f"{self.pds}/xrpc/com.atproto.repo.deleteRecord",
                headers={"Authorization": f"Bearer {self.jwt}"},
                json_body={"repo": self.did, "collection": "app.bsky.feed.post", "rkey": m.group(2)})

    def link_card(self, uri):
        """app.bsky.embed.external for uri, or None if the page can't be read."""
        try:
            info = link_preview(uri)
        except Exception as e:
            print(f"  no link card for {uri}: {e}")
            return None
        external = {"uri": uri, "title": info["title"], "description": info["description"]}
        if info["image"]:
            try:
                req = urllib.request.Request(info["image"], headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read(20_000_000)
                tmp = pathlib.Path("/tmp/crosspost-card")
                tmp.write_bytes(raw)
                data, ctype, _ = shrink(tmp, BLUESKY_IMAGE_MAX)
                external["thumb"] = request("POST", f"{self.pds}/xrpc/com.atproto.repo.uploadBlob",
                                            headers={"Authorization": f"Bearer {self.jwt}", "Content-Type": ctype},
                                            data=data)[1]["blob"]
            except Exception as e:
                print(f"  link card for {uri} without image: {e}")
        return {"$type": "app.bsky.embed.external", "external": external}

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
            if not images and facets:
                uri = facets[0]["features"][0]["uri"]
                try:
                    print(f"    link card for {uri}: {link_preview(uri)}")
                except Exception as e:
                    print(f"    link card for {uri}: none ({e})")
            return None
        if images:
            record["embed"] = {"$type": "app.bsky.embed.images", "images": [self.upload(p, a) for p, a in images]}
        elif facets:
            # Bluesky doesn't build link previews itself: attach a card for the first link.
            card = self.link_card(facets[0]["features"][0]["uri"])
            if card:
                record["embed"] = card
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
        text = post_text(post, site)
        images = post.images()
        if DRY_RUN:
            print(f"  Mastodon ({len(text)} chars, {len(images)} images):\n    " + text.replace("\n", "\n    "))
            return None
        body = {"status": text, "visibility": "public", "language": "en",
                "media_ids": [self.upload(p, a) for p, a in images]}
        res = request("POST", f"{self.base}/api/v1/statuses",
                      headers={**self.auth, "Idempotency-Key": f"{post.path}"}, json_body=body)[1]
        return f'mastodon:\n  id: "{res["id"]}"\n  username: "{self.username}"\n  hostname: "{self.instance}"\n'


# ---------------------------------------------------------------- /dev/null

class DevNull:
    BASE = "https://dev-null.sh"

    def __init__(self, public_key):
        self.public_key = str(pathlib.Path(public_key).expanduser())
        parts = pathlib.Path(self.public_key).read_text(encoding="utf-8").split()
        if len(parts) < 2 or parts[0] not in ("ssh-ed25519", "ssh-rsa"):
            raise ValueError("DEVNULL_PUBLIC_KEY must point to an Ed25519 or RSA public key, not a private key")
        key = " ".join(parts[:2])
        recognized = self.request("/api/cli/key-lookups", data=(key + "\n").encode(),
                                  headers={"Content-Type": "text/plain; charset=utf-8"})
        if recognized.strip() != key:
            raise RuntimeError("/dev/null did not recognize the configured public key")
        # Check the agent too: CHECK_LOGIN must catch a missing private key without posting.
        self.signature(b"Cross-post signing check", "devnull-commit")

    def request(self, path, **kwargs):
        # Unlike the other networks, the CLI returns plain text. Never redirect signed requests.
        return request("POST", self.BASE + path, text_response=True, follow_redirects=False, **kwargs)[1]

    def signature(self, payload, namespace):
        result = subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-n", namespace, "-f", self.public_key],
            input=payload, capture_output=True, timeout=30,
            env={**os.environ, "SSH_ASKPASS_REQUIRE": "never"},
        )
        if result.returncode:
            raise RuntimeError("/dev/null signing failed: load the configured key into ssh-agent")
        signature = b"".join(line for line in result.stdout.splitlines() if not line.startswith(b"-----")).decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", signature):
            raise RuntimeError("ssh-keygen returned an invalid signature")
        return signature

    def post(self, post, site):
        link = post.permalink(site)
        text = post_text(post, site) or link  # CLI requires text even with images
        if len(text) > DEVNULL_LIMIT:
            budget = DEVNULL_LIMIT - len(link) - 3  # ellipsis and two newlines
            if budget <= 0:
                raise ValueError("post permalink exceeds /dev/null's character limit")
            text = text[:budget].rstrip() + "…\n\n" + link
        images = post.images()[:3]
        if DRY_RUN:
            print(f"  /dev/null ({len(text)} chars, {len(images)} images):\n    " + text.replace("\n", "\n    "))
            return None

        # Match https://dev-null.sh/commit byte for byte: timestamp, nonce, empty reply,
        # optional comma-separated SHA-256 image hashes, then the message (no final newline).
        files, hashes = {}, []
        for i, (path, _) in enumerate(images):
            data, ctype, _ = shrink(path, DEVNULL_IMAGE_MAX, formats=("JPEG", "PNG", "WEBP"))
            hashes.append(hashlib.sha256(data).hexdigest())
            files[f"images[{i}]"] = (f"image-{i}", data, ctype)
        lines = [str(int(time.time())), uuid.uuid4().hex, ""]
        namespace = "devnull-commit"
        if images:
            namespace = "devnull-commit-images"
            lines.append(",".join(hashes))
        payload = "\n".join([*lines, text]).encode("utf-8")
        signature = self.signature(payload, namespace)
        if images:
            data, ctype = multipart({}, {"payload": ("commit", payload, "text/plain"), **files})
        else:
            data, ctype = payload, "text/plain; charset=utf-8"
        response = self.request("/api/cli/commits", data=data, timeout=600 if images else 60,
                                headers={"Content-Type": ctype, "X-SSH-Signature": signature})
        # A pending-review response has the same URL followed by a parenthesized note.
        match = re.search(r"^Committed: (https://dev-null\.sh/@[A-Za-z0-9_-]+/commits/[A-Za-z0-9-]+)(?:\s|$)", response)
        if not match:
            raise RuntimeError(f"/dev/null returned an unexpected commit response: {response[:500]}")
        url = match.group(1)
        return f"devnull:\n  id: {json.dumps(url.rsplit('/', 1)[1])}\n  url: {json.dumps(url)}\n"


# ---------------------------------------------------------------- Images

def shrink(path, max_bytes, *, formats=("JPEG", "PNG", "GIF", "WEBP")):
    """Return (bytes, content type, (w, h)); convert oversized/unsupported images to JPEG."""
    from PIL import Image, ImageOps

    raw = path.read_bytes()
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        size = im.size
        if len(raw) <= max_bytes and im.format in formats:
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
    status = None
    for _ in range(minutes * 4):
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return
                status = r.status
        except urllib.error.HTTPError as e:
            status = e.code
        except urllib.error.URLError as e:
            status = str(e.reason)
        print(f"  waiting for {url} (got {status})")
        time.sleep(15)
    raise RuntimeError(f"{url} is not live yet (last status: {status})")


def main():
    site = os.environ.get("SITE_URL", "https://juanvisbal.com")
    devnull_enabled = bool(os.environ.get("DEVNULL_PUBLIC_KEY")) or DRY_RUN
    if not devnull_enabled:
        print("/dev/null disabled: configure DEVNULL_PUBLIC_KEY and load its key into ssh-agent.")
    if os.environ.get("CHECK_LOGIN") == "1" and not DRY_RUN:
        bsky = Bluesky(os.environ["BLUESKY_HANDLE"], os.environ["BLUESKY_APP_PASSWORD"])
        masto = Mastodon(os.environ["MASTODON_INSTANCE"], os.environ["MASTODON_TOKEN"])
        print(f"Bluesky: logged in as {bsky.handle} ({bsky.did}) via {bsky.pds}")
        print(f"Mastodon: logged in as @{masto.username}@{masto.instance}")
        if devnull_enabled:
            devnull = DevNull(os.environ["DEVNULL_PUBLIC_KEY"])
            print(f"/dev/null: GitHub key recognized and agent signing works ({devnull.public_key})")
        return
    now = dt.datetime.now(dt.timezone.utc)

    def needs_devnull(post):
        return devnull_enabled and post.date.date() >= DEVNULL_SINCE and not post.has_block("devnull")

    pending = []
    for path in sorted(CONTENT.glob("[0-9][0-9][0-9][0-9]/**/*.md")):
        post = Post(path)
        if post.field("draft") == "true" or post.date.date() < CROSSPOST_SINCE or post.date > now:
            continue
        if not post.has_block("bluesky") or not post.has_block("mastodon") or needs_devnull(post):
            pending.append(post)
    pending.sort(key=lambda p: p.date)  # oldest first, so feeds keep the blog's order
    deletions = os.environ.get("BLUESKY_DELETE", "").split()
    if not pending and not deletions:
        print("Nothing to cross-post.")
        return

    # Log in only to the networks this run needs, each on its own: if one is
    # unreachable, the other still gets its posts.
    failures = 0
    needs_bsky = bool(deletions) or any(not p.has_block("bluesky") for p in pending)
    needs_masto = any(not p.has_block("mastodon") for p in pending)
    needs_null = any(needs_devnull(p) for p in pending)

    def login(cls, *env):
        if DRY_RUN:  # no logins; post() prints and returns before using the session
            return object.__new__(cls)
        try:
            return cls(*(os.environ[k] for k in env))
        except Exception as e:
            nonlocal failures
            failures += 1
            print(f"  {cls.__name__} login failed, skipping it this run: {e}", file=sys.stderr)
            return None

    bsky = login(Bluesky, "BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD") if needs_bsky else None
    masto = login(Mastodon, "MASTODON_INSTANCE", "MASTODON_TOKEN") if needs_masto else None
    devnull = login(DevNull, "DEVNULL_PUBLIC_KEY") if needs_null else None
    for at_uri in deletions if bsky else []:
        if DRY_RUN:
            print(f"would delete {at_uri}")
            continue
        try:
            bsky.delete(at_uri)
            print(f"deleted {at_uri}")
        except Exception as e:
            failures += 1
            print(f"  delete {at_uri} failed: {e}", file=sys.stderr)
    for post in pending:
        print(f"{post.path} -> {post.permalink(site)}")
        if not DRY_RUN:
            wait_until_live(post.permalink(site))
        for key, client in (("bluesky", bsky), ("mastodon", masto), ("devnull", devnull)):
            if post.has_block(key) or client is None or (key == "devnull" and not needs_devnull(post)):
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
