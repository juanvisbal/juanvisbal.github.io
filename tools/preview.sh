#!/bin/sh
# Hugo + the real Pages Functions, with a persistent local-only D1 database.
set -eu
cd "$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"

for tool in hugo wrangler; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Install %s before running the local preview.\n' "$tool" >&2
    exit 1
  fi
done

port=${PORT:-8788}
export WRANGLER_SEND_METRICS=false

# Both commands use the same local database key and storage directory. --local
# is deliberate: no Cloudflare login or production database access is needed.
CI=true wrangler d1 migrations apply HEARTS --local \
  --config tools/wrangler.local.toml --persist-to "$PWD/.wrangler/state" </dev/null

# Keep this output separate from `hugo server`'s public/ directory.
hugo --destination .wrangler/preview --baseURL "http://localhost:$port/"
hugo --watch --destination .wrangler/preview --baseURL "http://localhost:$port/" &
hugo_pid=$!
trap 'kill "$hugo_pid" 2>/dev/null || :; wait "$hugo_pid" 2>/dev/null || :' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

wrangler pages dev .wrangler/preview --d1 HEARTS \
  --persist-to "$PWD/.wrangler/state" --ip 127.0.0.1 --port "$port" \
  --compatibility-date 2026-10-01 --show-interactive-dev-session=false
