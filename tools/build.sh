#!/bin/sh
# Site build into public/: what Cloudflare Pages runs (build command `sh tools/build.sh`,
# output directory `public`). The project's build command is shared with `main`, which builds
# with HyperTemplates; on this branch it runs Hugo.
#
# Uses `hugo` from PATH if it is HUGO_VERSION, otherwise downloads that release into .bin/
# (gitignored; Linux only, which is what Cloudflare builds on).
set -eu
cd "$(dirname "$0")/.."

HUGO_VERSION=0.168.0

if command -v hugo >/dev/null 2>&1 && hugo version | grep -q "v$HUGO_VERSION"; then
  HUGO=$(command -v hugo)
else
  HUGO=.bin/hugo-$HUGO_VERSION
  if [ ! -x "$HUGO" ]; then
    os=$(uname -s | tr '[:upper:]' '[:lower:]')
    arch=$(uname -m)
    case "$arch" in x86_64) arch=amd64 ;; aarch64) arch=arm64 ;; esac
    if [ "$os" != linux ]; then
      echo "Install Hugo $HUGO_VERSION (extended), e.g. brew install hugo" >&2
      exit 1
    fi
    mkdir -p .bin
    echo "Downloading Hugo $HUGO_VERSION ($os/$arch)"
    curl -fsSL "https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_${os}-${arch}.tar.gz" | tar -xz -C .bin hugo
    mv .bin/hugo "$HUGO"
  fi
fi

"$HUGO" version
"$HUGO"
