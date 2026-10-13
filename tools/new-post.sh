#!/bin/sh
# New blog post: content/blog/YYYY/MM/DD/<slug>/index.md, published at /blog/YYYY/MM/DD/<slug>.html
#
#   tools/new-post.sh my-slug            a note (no title)
#   tools/new-post.sh my-slug "A title"  a titled post
#
# Write below the front matter; put images next to index.md and use ![alt](photo.jpg).
set -eu
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { sed -n '2,7s/^# \{0,1\}//p' "$0"; exit 1; }

slug=$1
dir=content/blog/$(date +%Y/%m/%d)/$slug
file=$dir/index.md
[ ! -e "$file" ] || { echo "$file already exists" >&2; exit 1; }
mkdir -p "$dir"
{
  echo "---"
  echo "created_at: $(date +%Y-%m-%dT%H:%M:%S%z | sed 's/\(..\)$/:\1/')"
  [ $# -ge 2 ] && printf 'title: "%s"\n' "$2"
  echo "layout: post"
  echo "ugly_url: true"
  echo "---"
  echo
} > "$file"
echo "$file"
