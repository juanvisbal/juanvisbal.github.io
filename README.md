# juanvisbal.com

Hugo site: the main pages and the blog (`/blog/`, migrated from Micro.blog on 2026-10-08). Built by Cloudflare Pages on every push (production branch `main`): build command `hugo`, output directory `public`, environment variable `HUGO_VERSION=0.167.0` (the build image default is older than this site needs).

Preview locally: `hugo server`, then open http://localhost:1313.

## Editing

| To change | Edit | Generated |
|---|---|---|
| Home links, bio, socials | `content/_index.md` | `/`, `/index.md` |
| Now | `content/now.md` (lists in front matter; bump `lastmod`) | `/now.html`, `/now.md` |
| Resume | `content/resume.md` | `/resume.html`, `/resume.md` |
| Blogroll | Replace `assets/blogroll.opml` with a NetNewsWire export; bump `lastmod` in `content/blogroll.md` | `/blogroll.html`, `/blogroll.md`, `/blogroll.opml` |
| Site nav | `[[menus.main]]` in `hugo.toml` | nav menus, `/llms.txt` page list |
| Static files (CSS, images, PDF, `human.json`, `CNAME`) | `static/` | copied as-is |

## Blog

- New post: `hugo new content blog/YYYY/MM/DD/<slug>.md`, write below the front matter, push.
- Images: `static/blog/uploads/YYYY/`, referenced as `/blog/uploads/...`.
- Feeds: `/blog/feed.xml` and `/blog/feed.json`. Imported posts keep their Micro.blog `guid`, so readers don't show them again.
- Theme: Minimism (MIT, see `layouts/blog/LICENSE-minimism`), with Micro.blog-only parts removed. Layouts in `layouts/blog/` apply only to `/blog/`; main-site layouts are at the top of `layouts/`.
- Replies: `data/blog/replies_*.json` (Micro.blog export) at `/blog/replies/`.
- `tools/import_microblog.py`: the one-off export cleanup.

## Hearts and comments

- Under each post: a ❤️ button and comments merged from the post's Bluesky and Mastodon copies (`layouts/_partials/blog/interactions.html`, `static/blog/assets/js/interactions.js`). Comments load in the browser from the public Bluesky and Mastodon APIs, using the `bluesky`/`mastodon` front matter of each post.
- Hearts: `functions/openheart/[[path]].js`, a Cloudflare Pages Function implementing [Open Heart](https://openheart.fyi), backed by the D1 database `juanvisbal-hearts` (bound as `HEARTS`; schema in `migrations/`). One heart per visitor per post per day; only a hash of IP + post + day is stored.
