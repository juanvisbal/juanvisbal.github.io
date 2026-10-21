// Mastodon replies, merged into the static list from the Micro.blog export on /blog/replies/.
// Built with DOM methods; remote HTML is converted, never inserted.
(() => {
  const main = document.getElementById("blog-replies");
  const list = main && main.querySelector(".post-list");
  const status = main && main.querySelector(".replies-status");
  const account = main && main.dataset.mastodonAccount;
  if (!list || !status || !account) return;

  // Mirrors blog/reply-network.html and site/post-date.html (which renders dates in Bogotá).
  const NAME = "Mastodon";
  const ICON = "fa-brands fa-mastodon";
  const ZONE = "America/Bogota";
  const MAX_PAGES = 3;

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

  // Mastodon HTML -> nodes, keeping only text, links, paragraphs and line breaks
  const mastodonHtml = (html) => {
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

  const dateLine = (when, url) => {
    const time = el("time", { datetime: when.toISOString() },
      when.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: ZONE }),
      el("span", { "aria-hidden": "true" }, " ·"), " ",
      when.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: ZONE }));
    const arrow = el("span", { "aria-hidden": "true" }, "\u2192 ");
    // The network sits after the time: "→ Aug 4, 2026 · 2:45 PM · 🦋".
    const icon = el("span", { class: "reply-network" },
      el("span", { "aria-hidden": "true" }, " \u00b7 "),
      el("i", { class: ICON, "aria-hidden": "true" }),
      " ",
      el("span", { class: "visually-hidden" }, NAME));
    return el("p", { class: "post-date" }, el("a", { href: url }, arrow, time, icon));
  };

  // Newest first: slot each reply in above the first older row already on the page.
  const insert = (li, when) => {
    for (const row of list.children) {
      const t = row.querySelector("time[datetime]");
      if (t && new Date(t.dateTime) < when) return list.insertBefore(li, row);
    }
    list.append(li);
  };

  const get = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  };

  status.textContent = "Loading Mastodon replies\u2026";
  (async () => {
    try {
      const { id } = await get(`https://social.lol/api/v1/accounts/lookup?acct=${encodeURIComponent(account)}`);
      const statuses = [];
      let before = "";
      for (let page = 0; page < MAX_PAGES; page++) {
        const batch = await get(`https://social.lol/api/v1/accounts/${id}/statuses?exclude_replies=false&limit=40${before ? `&max_id=${before}` : ""}`);
        statuses.push(...batch);
        if (batch.length < 40) break;
        before = batch[batch.length - 1].id;
      }
      const replies = statuses.filter((s) => s.in_reply_to_id && s.content);
      for (const s of replies.reverse()) { // oldest first, insert() keeps the list sorted
        const when = new Date(s.created_at);
        insert(el("li", { "data-network": NAME },
          el("div", { class: "post-body" }, mastodonHtml(s.content)),
          dateLine(when, s.url)), when);
      }
      status.textContent = "";
    } catch {
      status.textContent = "Mastodon replies couldn\u2019t be loaded right now.";
    }
  })();
})();
