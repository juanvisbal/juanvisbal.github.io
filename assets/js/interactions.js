// Hearts (Open Heart) and comments merged from a post's Bluesky and Mastodon copies.
// Everything is built with DOM methods; remote text is never inserted as HTML.
(() => {
  const root = document.getElementById("interactions");
  if (!root) return;

  const HEART = "❤️";
  const MAX_DEPTH = 3;

  // ---------- Hearts ----------
  // Click to heart, click again to unheart. The browser keeps a random visitor id
  // (localStorage) that the server uses to find this browser's heart when unhearting.

  const heartButton = root.querySelector(".heart-button");
  const heartCount = root.querySelector(".heart-count");
  const heartLabel = root.querySelector(".heart-label");
  const heartUrl = root.dataset.heart;
  const storageKey = "hearted:" + heartUrl;

  const store = {
    get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
    set: (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  const visitorId = () => {
    let id = store.get("openheart-visitor");
    if (!id) {
      id = crypto.randomUUID();
      store.set("openheart-visitor", id);
    }
    return id;
  };
  const hearted = () => store.get(storageKey) === "1";

  let count = 0;
  let busy = false;
  const renderHeart = () => {
    heartCount.textContent = count > 0 ? String(count) : "";
    heartButton.setAttribute("aria-pressed", hearted() ? "true" : "false");
    const total = count === 1 ? "1 heart" : `${count} hearts`;
    // The visible count comes first, so voice control ("tap 3") matches the name.
    heartButton.setAttribute("aria-label", count > 0 ? `${total}. ${hearted() ? "Remove your heart" : "Send a heart"}` : (hearted() ? "Remove your heart" : "Send a heart"));
    heartLabel.textContent = "";
    heartButton.hidden = false;
  };

  const send = async (method, body) => {
    const r = await fetch(heartUrl, { method, body, headers: { "Content-Type": "text/plain;charset=UTF-8" } });
    const data = await r.json().catch(() => ({}));
    return { status: r.status, count: Number(data[HEART]) || 0 };
  };

  if (heartButton && heartUrl) {
    fetch(heartUrl, { headers: { Accept: "application/json" } })
      .then((r) => (r.ok ? r.json() : {}))
      .then((counts) => { count = Number(counts[HEART]) || 0; renderHeart(); })
      .catch(() => {});

    heartButton.addEventListener("click", async () => {
      if (busy) return;
      busy = true;
      const unheart = hearted();
      // Optimistic update; corrected by the server's count below.
      store.set(storageKey, unheart ? null : "1");
      count = Math.max(count + (unheart ? -1 : 1), 0);
      renderHeart();
      try {
        const r = unheart ? await send("DELETE", visitorId()) : await send("POST", HEART + "\n" + visitorId());
        // 409 = already hearted from this browser; 429 = daily limit from this network.
        if (!unheart && r.status === 429) store.set(storageKey, null);
        count = r.count;
      } catch { /* offline: keep the optimistic state */ }
      busy = false;
      renderHeart();
    });
  }

  // ---------- Comments ----------

  const list = root.querySelector(".comment-list");
  const status = root.querySelector(".comments-status");
  if (!list) return;

  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v !== undefined && v !== null) node.setAttribute(k, v);
    }
    for (const c of children) node.append(c);
    return node;
  };

  const safeHref = (url) => {
    try {
      const u = new URL(url);
      return u.protocol === "https:" || u.protocol === "http:" ? u.href : null;
    } catch { return null; }
  };

  const link = (href, text) => {
    const safe = safeHref(href);
    return safe ? el("a", { href: safe, rel: "nofollow ugc noopener" }, text) : document.createTextNode(text);
  };

  // Bluesky text + facets (byte offsets into UTF-8) -> nodes
  const blueskyText = (text, facets = []) => {
    const bytes = new TextEncoder().encode(text);
    const dec = new TextDecoder();
    const sorted = [...facets].sort((a, b) => a.index.byteStart - b.index.byteStart);
    const out = [];
    let pos = 0;
    for (const f of sorted) {
      const { byteStart, byteEnd } = f.index;
      if (byteStart < pos || byteEnd > bytes.length) continue;
      out.push(document.createTextNode(dec.decode(bytes.slice(pos, byteStart))));
      const label = dec.decode(bytes.slice(byteStart, byteEnd));
      const feature = (f.features || [])[0] || {};
      if (feature.$type === "app.bsky.richtext.facet#link") out.push(link(feature.uri, label));
      else if (feature.$type === "app.bsky.richtext.facet#mention") out.push(link("https://bsky.app/profile/" + feature.did, label));
      else if (feature.$type === "app.bsky.richtext.facet#tag") out.push(link("https://bsky.app/hashtag/" + encodeURIComponent(feature.tag), label));
      else out.push(document.createTextNode(label));
      pos = byteEnd;
    }
    out.push(document.createTextNode(dec.decode(bytes.slice(pos))));
    return el("p", {}, ...out);
  };

  // Mastodon HTML -> nodes, keeping only text, links, paragraphs and line breaks
  const mastodonContent = (html) => {
    const doc = new DOMParser().parseFromString(html, "text/html");
    const convert = (node) => {
      if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent);
      if (node.nodeType !== Node.ELEMENT_NODE) return null;
      const kids = [...node.childNodes].map(convert).filter(Boolean);
      const tag = node.tagName.toLowerCase();
      if (tag === "a") return link(node.getAttribute("href"), node.textContent);
      if (tag === "br") return el("br");
      if (tag === "p") return el("p", {}, ...kids);
      const frag = document.createDocumentFragment();
      frag.append(...kids);
      return frag;
    };
    const frag = document.createDocumentFragment();
    frag.append(...[...doc.body.childNodes].map(convert).filter(Boolean));
    return frag;
  };

  const blueskyComments = async (uri) => {
    const api = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?depth=10&uri=" + encodeURIComponent(uri);
    const r = await fetch(api);
    if (!r.ok) throw new Error("Bluesky " + r.status);
    const { thread } = await r.json();
    const ownerDid = uri.split("/")[2]; // at://<did>/app.bsky.feed.post/<rkey>
    const out = [];
    const walk = (node, depth, parentName) => {
      for (const reply of node.replies || []) {
        if (reply.$type !== "app.bsky.feed.defs#threadViewPost") continue;
        const p = reply.post;
        // Authors who opted out of being shown to logged-out viewers (as bsky.app does),
        // except the blog's own author.
        const optedOut = (p.author.labels || []).some((l) => l.val === "!no-unauthenticated");
        if (optedOut && p.author.did !== ownerDid) {
          walk(reply, depth, parentName);
          continue;
        }
        const rkey = p.uri.split("/").pop();
        out.push({
          network: "Bluesky",
          name: p.author.displayName || p.author.handle,
          handle: "@" + p.author.handle,
          avatar: p.author.avatar,
          profile: "https://bsky.app/profile/" + p.author.handle,
          url: "https://bsky.app/profile/" + p.author.handle + "/post/" + rkey,
          date: new Date(p.record.createdAt || p.indexedAt),
          likes: p.likeCount || 0,
          depth,
          replyTo: depth > 0 ? parentName : null,
          body: blueskyText(p.record.text || "", p.record.facets),
        });
        walk(reply, depth + 1, p.author.displayName || p.author.handle);
      }
    };
    walk(thread, 0, null);
    return out;
  };

  const mastodonComments = async (api) => {
    const r = await fetch(api + "/context");
    if (!r.ok) throw new Error("Mastodon " + r.status);
    const { descendants } = await r.json();
    const rootId = api.split("/").pop();
    const depthOf = new Map([[rootId, -1]]);
    const nameOf = new Map();
    return descendants.map((s) => {
      const depth = (depthOf.get(s.in_reply_to_id) ?? -1) + 1;
      depthOf.set(s.id, depth);
      nameOf.set(s.id, s.account.display_name || s.account.username);
      return {
        network: "Mastodon",
        name: s.account.display_name || s.account.username,
        handle: "@" + s.account.acct,
        avatar: s.account.avatar_static || s.account.avatar,
        profile: s.account.url,
        url: s.url || s.uri,
        date: new Date(s.created_at),
        likes: s.favourites_count || 0,
        depth,
        replyTo: depth > 0 ? nameOf.get(s.in_reply_to_id) : null,
        body: mastodonContent(s.content || ""),
      };
    });
  };

  const render = (c) => {
    const when = c.date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const avatarSafe = safeHref(c.avatar);
    const meta = el("div", { class: "comment-meta" },
      avatarSafe ? el("img", { class: "comment-avatar", src: avatarSafe, alt: "", width: "32", height: "32", loading: "lazy" }) : "",
      el("span", { class: "comment-author" }, link(c.profile, c.name), " ", el("span", { class: "comment-handle" }, c.handle)),
    );
    const footer = el("div", { class: "comment-footer" },
      link(c.url, when + " on " + c.network),
      c.likes ? " · " + c.likes + (c.likes === 1 ? " like" : " likes") : "",
    );
    const replyNote = c.replyTo ? el("span", { class: "visually-hidden" }, `Reply to ${c.replyTo}: `) : "";
    return el("li", { class: "comment", "data-depth": String(Math.min(c.depth, MAX_DEPTH)) }, replyNote, meta, el("div", { class: "comment-body" }, c.body), footer);
  };

  const sources = [];
  if (root.dataset.blueskyPost) sources.push(blueskyComments(root.dataset.blueskyPost));
  if (root.dataset.mastodonApi) sources.push(mastodonComments(root.dataset.mastodonApi));
  if (!sources.length) return;

  status.textContent = "Loading comments…";
  Promise.allSettled(sources).then((results) => {
    const failed = results.filter((r) => r.status === "rejected").length;
    // Each network returns replies depth-first (parent, then its replies). Keep that order
    // within a thread, and interleave whole top-level threads from both networks by date.
    const threads = [];
    let comments = 0;
    for (const r of results) {
      if (r.status !== "fulfilled") continue;
      let current = null;
      for (const c of r.value) {
        if (c.depth === 0 || !current) {
          current = { date: c.date, items: [] };
          threads.push(current);
        }
        current.items.push(c);
        comments++;
      }
    }
    threads.sort((a, b) => a.date - b.date);
    for (const t of threads) for (const c of t.items) list.append(render(c));
    status.textContent = comments
      ?(failed ? "Some comments couldn’t be loaded." : "")
      : (failed ? "Comments couldn’t be loaded right now." : "No comments yet.");
  });
})();
