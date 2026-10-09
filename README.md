# juanvisbal.com

Hugo site: the main pages and the blog (`/blog/`, migrated from Micro.blog on 2026-10-08). Built by Cloudflare Pages on every push (production branch `main`): build command `hugo`, output directory `public`, environment variable `HUGO_VERSION=0.167.0` (the build image default is older than this site needs).

Preview locally: `hugo server`, then open http://localhost:1313.

## Editing

| To change | Edit | Generated |
|---|---|---|
| Home links, bio, socials | `content/_index.md` | `/`, `/index.md` |
| Now | `content/now.md`: plain Markdown, one `## Heading` + list per card (icons in front matter); bump `lastmod` | `/now.html`, `/now.md` |
| Resume | `content/resume.md` | `/resume.html`, `/resume.md` |
| Blogroll | Replace `assets/blogroll.opml` with a NetNewsWire export; bump `lastmod` in `content/blogroll.md` | `/blogroll.html`, `/blogroll.md`, `/blogroll.opml` |
| Site nav | `[[menus.main]]` in `hugo.toml` | nav menus, `/llms.txt` page list |
| CSS and JS | `assets/stylesheets/`, `assets/js/` | fingerprinted URLs (`layouts/_partials/site/css.html`, `js.html`), so browsers never use a stale copy |
| Static files (images, PDF, `human.json`, `CNAME`) | `static/` | copied as-is |

## Blog

- New post: `hugo new content blog/YYYY/MM/DD/<slug>.md`, write below the front matter, push.
- Images: `static/blog/uploads/YYYY/`, referenced as `/blog/uploads/...`.
- Feeds: `/blog/feed.xml` and `/blog/feed.json`. Imported posts keep their Micro.blog `guid`, so readers don't show them again.
- Design: the blog uses the main site's layout (`layouts/baseof.html`) and stylesheets, plus `assets/stylesheets/blog.css`. Templates in `layouts/blog/` apply only to `/blog/`. The feed templates started from Minimism (MIT, see `layouts/blog/LICENSE-minimism`).
- Replies: `data/blog/replies_*.json` (Micro.blog export) at `/blog/replies/`.
- `tools/import_microblog.py`: the one-off export cleanup.

## Hearts and comments

- Under each post: a ❤️ button and comments merged from the post's Bluesky and Mastodon copies (`layouts/_partials/blog/interactions.html`, `assets/js/interactions.js`). Comments load in the browser from the public Bluesky and Mastodon APIs, using the `bluesky`/`mastodon` front matter of each post. Bluesky accounts that opted out of being shown to logged-out viewers (`!no-unauthenticated`) are skipped, except your own.
- Hearts: `functions/openheart/[[path]].js`, a Cloudflare Pages Function implementing [Open Heart](https://openheart.fyi), backed by the D1 database `juanvisbal-hearts` (bound as `HEARTS`; schema in `migrations/`). One heart per visitor per post per day; only a hash of IP + post + day is stored. Clicking again unhearts: the button sends a random per-browser ID (stored hashed) with the heart, and `DELETE` with that ID removes it (an extension to Open Heart).

## Cross-posting

`.github/workflows/crosspost.yaml` runs `tools/crosspost.py` after each push to `main` that touches `content/blog/`. New posts (dated 2026-10-01 or later, not drafts, not in the future) go to Bluesky (`juanvisbal.com`) and Mastodon (`@juan@social.lol`); the links to those copies are committed back into the post's front matter, which turns on its comments box. Short posts are posted in full; titled posts as title + link; long posts are shortened on Bluesky (300 characters) with a link. Up to 4 images, with alt text. Secrets: `BLUESKY_APP_PASSWORD`, `MASTODON_TOKEN`. To test the logins without posting: Actions → "Cross-post new blog posts" → Run workflow → tick "Only check".

## Light/dark theme

Colours are tokens in `assets/stylesheets/tokens.css` (`light-dark()`, with a system-preference fallback). The footer button (`layouts/_partials/site/theme-toggle.html`, `assets/js/theme.js`) toggles between following the system and the opposite theme, stored in `localStorage`; an inline script in `<head>` applies it before the page renders.

## Shared layout pieces

`layouts/_partials/site/`: `head-common.html` (theme setup, favicons, feeds, stylesheet), `nav.html` (breadcrumb + menu), `page-header.html` (title, `note` from front matter, optional intro/subnav), `footer.html` (with the theme toggle), `scripts.html`, `css.html`/`js.html` (fingerprinted assets).
