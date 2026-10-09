// Open Heart endpoint (https://openheart.fyi) for blog posts.
//   GET  /openheart/blog/YYYY/MM/DD/slug.html -> {"❤️": 3}
//   POST /openheart/blog/YYYY/MM/DD/slug.html with body "❤️" -> adds one heart
// Storage: D1 database bound as HEARTS (schema in migrations/).

const ALLOWED = ["❤️"];
const POST_PATH = /^\/blog\/\d{4}\/\d{2}\/\d{2}\/[a-z0-9-]+\.html$/;

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });

async function counts(db, path) {
  const { results } = await db.prepare("SELECT emoji, count FROM hearts WHERE path = ?").bind(path).all();
  return Object.fromEntries(results.map((r) => [r.emoji, r.count]));
}

async function sha256(text) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The message is one emoji sequence, optionally followed by data the server ignores
// (e.g. "❤️=" from an HTML form). A bare "❤" counts as "❤️".
function parseEmoji(body) {
  const text = body.trim().replace(/^❤(?!️)/, "❤️");
  return ALLOWED.find((e) => text.startsWith(e));
}

export async function onRequest({ request, env, params }) {
  const path = "/" + [].concat(params.path || []).join("/");
  if (!POST_PATH.test(path)) return json({ error: "not a blog post" }, 404);

  if (request.method === "GET") return json(await counts(env.HEARTS, path));
  if (request.method !== "POST") return json({ error: "method not allowed" }, 405);

  const emoji = parseEmoji(await request.text());
  if (!emoji) return json({ error: "unsupported emoji" }, 400);

  // Only real posts: ask the static site whether the page exists.
  const page = await env.ASSETS.fetch(new URL(path, request.url), { redirect: "manual" });
  if (page.status === 404) return json({ error: "not a blog post" }, 404);

  const day = new Date().toISOString().slice(0, 10);
  const ip = request.headers.get("CF-Connecting-IP") || "";
  const key = await sha256(`${ip}|${path}|${day}`);

  const vote = await env.HEARTS.prepare("INSERT OR IGNORE INTO heart_votes (key, day) VALUES (?, ?)").bind(key, day).run();
  if (vote.meta.changes === 0) return json(await counts(env.HEARTS, path), 429);

  await env.HEARTS.batch([
    env.HEARTS.prepare(
      "INSERT INTO hearts (path, emoji, count) VALUES (?, ?, 1) ON CONFLICT (path, emoji) DO UPDATE SET count = count + 1"
    ).bind(path, emoji),
    env.HEARTS.prepare("DELETE FROM heart_votes WHERE day < date(?, '-2 days')").bind(day),
  ]);
  return json(await counts(env.HEARTS, path));
}
