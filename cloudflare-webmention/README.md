# Cloudflare Webmention endpoint (minimal)

This is a minimal self-hosted Webmention receiver for `juanvisbal.com`.

## What it does

- Exposes `GET` and `POST` endpoint logic for `/webmention`
- Accepts incoming Webmentions (`source`, `target`)
- Validates that `target` is on an allowed origin
- Fetches `source` and verifies it links to `target`
- Stores accepted mentions in Cloudflare KV (`WEBMENTIONS`)

## 1) Prerequisites

- Cloudflare account with `juanvisbal.com` zone
- Node + npm (for Wrangler CLI)

## 2) Create KV namespace

In Cloudflare dashboard (Workers & Pages -> KV):

- Create a namespace, e.g. `webmentions`
- Copy the namespace ID

Then update `wrangler.toml`:

- Replace `REPLACE_WITH_KV_NAMESPACE_ID` with your namespace ID

## 3) Install and authenticate Wrangler

```bash
npm install -g wrangler
wrangler login
```

## 4) Deploy worker

From this directory:

```bash
wrangler deploy
```

## 5) Bind route to your domain

In Cloudflare dashboard for the worker:

- Add route: `juanvisbal.com/webmention*`

This makes `https://juanvisbal.com/webmention` hit this Worker.

## 6) Update site discovery tags

Your homepage should advertise your endpoint:

```html
<link rel="webmention" href="https://juanvisbal.com/webmention" />
```

You can remove `pingback` unless you run an XML-RPC pingback endpoint.

## 7) Quick test

```bash
curl -i -X POST "https://juanvisbal.com/webmention" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "source=https://example.com/post&target=https://juanvisbal.com/"
```

Expected on success: `202 Accepted` JSON response.

## Notes / limitations (MVP)

- Minimal link detection (string match)
- No spam filtering yet
- No microformats parsing yet
- No public listing UI yet

This is intentionally small to get you self-hosted quickly. You can iterate from here.
