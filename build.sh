#!/usr/bin/env bash
# Cloudflare Pages build command: `bash build.sh` (output directory: public).
# Pins Hugo here so the build doesn't depend on the build image's default version.
set -euo pipefail

HUGO_VERSION=0.167.0

if ! hugo version 2>/dev/null | grep -q "v${HUGO_VERSION}"; then
  tmp="$(mktemp -d)"
  file="hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz"
  base="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}"
  curl -fsSL -o "${tmp}/${file}" "${base}/${file}"
  curl -fsSL -o "${tmp}/checksums.txt" "${base}/hugo_${HUGO_VERSION}_checksums.txt"
  (cd "${tmp}" && grep " ${file}\$" checksums.txt | sha256sum -c -)
  tar -xzf "${tmp}/${file}" -C "${tmp}" hugo
  export PATH="${tmp}:${PATH}"
fi

hugo version
hugo build --gc --logLevel warn --panicOnWarning
