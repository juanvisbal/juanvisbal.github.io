// Open Heart endpoint for Cloudflare Pages Functions, backed by D1.
//   GET    /openheart<path>                 -> {"❤️": 3}
//   POST   /openheart<path>  body "❤️"      -> adds one heart
//   DELETE /openheart<path>  body "<visitor id>" -> removes that visitor's heart
//
// Unhearting is an extension: the button sends "❤️\n<visitor id>" (the protocol lets a
// server ignore data after the emoji) and DELETE with that id removes the heart.
// Protocol: https://openheart.fyi
//
// Vendored: juanvisbal.com keeps a verbatim copy of this file (and the migrations) at
// functions/openheart/[[path]].js. Change it here, then run `tools/sync-hearts.py` there.

// Which emoji this endpoint accepts. The first one is the one DELETE decrements.
// Must match client/openheart.js.
const EMOJIS = ["❤️"];

// Which page paths may be hearted. `path` arrives without the function's own prefix,
// so "/openheart/blog/2026/10/13/hello.html" is matched as "/blog/2026/10/13/hello.html".
const PATH_PATTERN = /^\/blog\/\d{4}\/\d{2}\/\d{2}\/[a-z0-9-]+\.html$/;

// The random id the browser keeps (localStorage) and sends to unheart.
const VISITOR_ID = /^[0-9a-f-]{36}$/;

// Vote rows older than this are pruned on every heart.
const VOTE_RETENTION_DAYS = 2;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

async function counts(db, path) {
  const { results } = await db.prepare("SELECT emoji, count FROM hearts WHERE path = ? AND count > 0").bind(path).all();
  return Object.fromEntries(results.map((r) => [r.emoji, r.count]));
}

async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The message is one emoji sequence, optionally followed by data (e.g. "❤️=" from an
// HTML form, or "❤️\n<visitor id>" from the button). A bare "❤" counts as "❤️".
function parseMessage(body) {
  const text = body.trim().replace(/^❤(?!️)/, "❤️");
  const emoji = EMOJIS.find((e) => text.startsWith(e));
  const id = text.slice(emoji ? emoji.length : 0).trim();
  return { emoji, visitorId: VISITOR_ID.test(id) ? id : null };
}

// One heart per network address per post per day; only a hash of it is stored.
async function dailyKey(request, path) {
  const day = new Date().toISOString().slice(0, 10);
  const forwarded = request.headers.get("x-forwarded-for");
  const ip = request.headers.get("CF-Connecting-IP") || (forwarded ? forwarded.split(",")[0].trim() : "");
  return { day, key: await sha256(`${ip}|${path}|${day}`) };
}

export async function onRequest({ request, env, params }) {
  const db = env.HEARTS;
  if (!db) return json({ error: "HEARTS binding missing" }, 500);

  const path = "/" + [].concat(params.path || []).join("/");
  if (!PATH_PATTERN.test(path)) return json({ error: "not a heartable page" }, 404);

  if (request.method === "GET") return json(await counts(db, path));

  if (request.method === "POST") {
    const { emoji, visitorId } = parseMessage(await request.text());
    if (!emoji) return json({ error: "unsupported emoji" }, 400);

    // Only real pages: ask the static site whether the page exists (Pages answers
    // 308 for an existing .html page and 404 for a missing one). Requires the Pages
    // ASSETS binding; without it, any path matching PATH_PATTERN is accepted.
    if (env.ASSETS) {
      const page = await env.ASSETS.fetch(new URL(path, request.url), { redirect: "manual" });
      if (page.status >= 400) return json({ error: "not a heartable page" }, 404);
    }

    const visitor = visitorId && (await sha256(visitorId));
    if (visitor) {
      const seen = await db.prepare("SELECT 1 FROM heart_visitors WHERE path = ? AND visitor = ?").bind(path, visitor).first();
      if (seen) return json(await counts(db, path), 409);
    }

    const { day, key } = await dailyKey(request, path);
    const vote = await db.prepare("INSERT OR IGNORE INTO heart_votes (key, day) VALUES (?, ?)").bind(key, day).run();
    if (vote.meta.changes === 0) return json(await counts(db, path), 429);

    const writes = [
      db.prepare(
        "INSERT INTO hearts (path, emoji, count) VALUES (?, ?, 1) ON CONFLICT (path, emoji) DO UPDATE SET count = count + 1"
      ).bind(path, emoji),
      db.prepare("DELETE FROM heart_votes WHERE day < date(?, ?)").bind(day, `-${VOTE_RETENTION_DAYS} days`),
    ];
    if (visitor) writes.push(db.prepare("INSERT OR IGNORE INTO heart_visitors (path, visitor) VALUES (?, ?)").bind(path, visitor));
    await db.batch(writes);
    return json(await counts(db, path));
  }

  if (request.method === "DELETE") {
    const id = (await request.text()).trim();
    if (!VISITOR_ID.test(id)) return json({ error: "missing visitor id" }, 400);
    const visitor = await sha256(id);
    const removed = await db.prepare("DELETE FROM heart_visitors WHERE path = ? AND visitor = ?").bind(path, visitor).run();
    if (removed.meta.changes === 0) return json(await counts(db, path), 404);

    const { key } = await dailyKey(request, path);
    await db.batch([
      db.prepare("UPDATE hearts SET count = MAX(count - 1, 0) WHERE path = ? AND emoji = ?").bind(path, EMOJIS[0]),
      // Let the same visitor heart again today after changing their mind.
      db.prepare("DELETE FROM heart_votes WHERE key = ?").bind(key),
    ]);
    return json(await counts(db, path));
  }

  return json({ error: "method not allowed" }, 405);
}
