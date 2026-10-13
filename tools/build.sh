#!/bin/sh
# Full site build into public/: what Cloudflare Pages runs (build command `sh tools/build.sh`,
# output directory `public`).
#
#   1. link-preview cards for posts (data/link_previews.json)  tools/build_extras.py previews
#   2. the site itself                                          hyperctl build
#   3. RSS/JSON feeds, Markdown copies, llms.txt, sitemap, cards tools/build_extras.py extras
#
# Uses `hyperctl` from PATH, or downloads HYPERCTL_VERSION into .bin/ (gitignored).
set -eu
cd "$(dirname "$0")/.."

HYPERCTL_VERSION=0.23.0

if command -v hyperctl >/dev/null 2>&1; then
  HYPERCTL=$(command -v hyperctl)
else
  HYPERCTL=.bin/hyperctl-$HYPERCTL_VERSION
  if [ ! -x "$HYPERCTL" ]; then
    os=$(uname -s | tr '[:upper:]' '[:lower:]')
    arch=$(uname -m)
    case "$arch" in x86_64) arch=amd64 ;; aarch64) arch=arm64 ;; esac
    mkdir -p .bin
    echo "Downloading hyperctl $HYPERCTL_VERSION ($os/$arch)"
    curl -fsSL "https://hypertemplates.net/downloads/hyperctl_v${HYPERCTL_VERSION}_${os}_${arch}.tar.gz" | tar -xz -C .bin
    mv .bin/hyperctl "$HYPERCTL"
  fi
fi
export HYPERCTL

# Cache-busting ?v= on CSS/JS URLs (env.version in the layouts).
HT_version=${CF_PAGES_COMMIT_SHA:-$(git rev-parse HEAD 2>/dev/null || date +%s)}
export HT_version=$(printf %.12s "$HT_version")

python3 tools/build_extras.py previews
rm -rf builds/public public
"$HYPERCTL" build -i public
mv builds/public public
python3 tools/build_extras.py extras public
