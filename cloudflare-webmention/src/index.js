const USER_AGENT = "juanvisbal-webmention/1.0 (+https://juanvisbal.com)";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET") {
      return handleGet(url);
    }

    if (request.method === "POST") {
      return handlePost(request, env, ctx);
    }

    return new Response("Method not allowed", {
      status: 405,
      headers: { Allow: "GET, POST" },
    });
  },
};

function handleGet(url) {
  const source = url.searchParams.get("source");
  const target = url.searchParams.get("target");

  if (source && target) {
    const body = {
      message:
        "Status checks are not implemented in this minimal endpoint yet. Re-submit your source/target with POST for processing.",
      source,
      target,
    };
    return json(body, 200);
  }

  return new Response(
    [
      "Webmention endpoint is active.",
      "",
      "POST source and target as x-www-form-urlencoded:",
      "source=https://example.com/post&target=https://juanvisbal.com/page",
    ].join("\n"),
    {
      status: 200,
      headers: { "content-type": "text/plain; charset=utf-8" },
    }
  );
}

async function handlePost(request, env) {
  const contentType = request.headers.get("content-type") || "";

  let source = "";
  let target = "";

  if (contentType.includes("application/x-www-form-urlencoded")) {
    const text = await request.text();
    const params = new URLSearchParams(text);
    source = normalizeMaybeUrl(params.get("source"));
    target = normalizeMaybeUrl(params.get("target"));
  } else if (contentType.includes("multipart/form-data")) {
    const form = await request.formData();
    source = normalizeMaybeUrl(form.get("source"));
    target = normalizeMaybeUrl(form.get("target"));
  } else if (contentType.includes("application/json")) {
    const body = await request.json().catch(() => ({}));
    source = normalizeMaybeUrl(body.source);
    target = normalizeMaybeUrl(body.target);
  } else {
    return json(
      {
        error:
          "Unsupported content type. Use application/x-www-form-urlencoded (preferred), multipart/form-data, or application/json.",
      },
      415
    );
  }

  if (!source || !target) {
    return json({ error: "Missing source or target." }, 400);
  }

  let sourceUrl;
  let targetUrl;
  try {
    sourceUrl = new URL(source);
    targetUrl = new URL(target);
  } catch {
    return json({ error: "source and target must be valid absolute URLs." }, 400);
  }

  if (!["http:", "https:"].includes(sourceUrl.protocol)) {
    return json({ error: "source must use http or https." }, 400);
  }

  if (!["http:", "https:"].includes(targetUrl.protocol)) {
    return json({ error: "target must use http or https." }, 400);
  }

  const allowedOrigins = parseAllowedOrigins(env.ALLOWED_TARGET_ORIGINS);
  if (!allowedOrigins.has(targetUrl.origin)) {
    return json(
      {
        error: "target is not on an allowed origin.",
        allowed_origins: Array.from(allowedOrigins),
      },
      400
    );
  }

  const sourceResponse = await fetch(sourceUrl.toString(), {
    headers: {
      "user-agent": USER_AGENT,
      accept: "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
    },
    redirect: "follow",
  }).catch(() => null);

  if (!sourceResponse || !sourceResponse.ok) {
    return json(
      {
        error: "Could not fetch source URL.",
        source_status: sourceResponse ? sourceResponse.status : null,
      },
      400
    );
  }

  const sourceBody = await sourceResponse.text();
  const linkFound = sourceContainsLinkToTarget(sourceBody, targetUrl);

  if (!linkFound) {
    return json(
      {
        error: "Source does not contain a link to target.",
        source: sourceUrl.toString(),
        target: targetUrl.toString(),
      },
      400
    );
  }

  const id = await makeId(sourceUrl.toString(), targetUrl.toString());
  const now = new Date().toISOString();

  const mention = {
    id,
    source: sourceUrl.toString(),
    target: targetUrl.toString(),
    receivedAt: now,
    sourceStatus: sourceResponse.status,
  };

  if (env.WEBMENTIONS) {
    await env.WEBMENTIONS.put(`mention:${id}`, JSON.stringify(mention));
  }

  return json(
    {
      status: "accepted",
      id,
      source: mention.source,
      target: mention.target,
      receivedAt: mention.receivedAt,
    },
    202,
    {
      Location: `/webmention?source=${encodeURIComponent(
        mention.source
      )}&target=${encodeURIComponent(mention.target)}`,
    }
  );
}

function parseAllowedOrigins(raw) {
  const fallback = ["https://juanvisbal.com", "https://www.juanvisbal.com"];
  const origins = (raw || fallback.join(","))
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  const set = new Set();
  for (const origin of origins) {
    try {
      const parsed = new URL(origin);
      set.add(parsed.origin);
    } catch {
      // ignore invalid entries
    }
  }

  if (set.size === 0) {
    set.add("https://juanvisbal.com");
  }

  return set;
}

function normalizeMaybeUrl(value) {
  if (typeof value !== "string") return "";
  return value.trim();
}

function sourceContainsLinkToTarget(html, targetUrl) {
  const candidates = new Set([
    targetUrl.toString(),
    stripTrailingSlash(targetUrl.toString()),
    targetUrl.origin + targetUrl.pathname,
    stripTrailingSlash(targetUrl.origin + targetUrl.pathname),
  ]);

  const decoded = html.replace(/&amp;/g, "&");

  for (const candidate of candidates) {
    if (candidate && decoded.includes(candidate)) {
      return true;
    }
  }

  return false;
}

function stripTrailingSlash(value) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

async function makeId(source, target) {
  const input = `${source}=>${target}`;
  const digest = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(input)
  );
  const bytes = new Uint8Array(digest).slice(0, 12);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function json(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...extraHeaders,
    },
  });
}
