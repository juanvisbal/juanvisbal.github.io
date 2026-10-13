# juanvisbal.com

[HyperTemplates](https://hypertemplates.net) site: the main pages and the blog (`/blog/`, migrated from Micro.blog on 2026-10-08). Built by Cloudflare Pages on every push (production branch `main`): build command `sh tools/build.sh`, output directory `public`.

- Preview locally: `hyperctl dev server`, then open http://localhost:8080 (pages and the Atom feed; live reload). For everything, including the RSS/JSON feeds, `.md` copies and link-preview cards: `sh tools/build.sh`, then serve `public/` (e.g. `python3 -m http.server -d public`).
- `hyperctl` (pinned in `tools/build.sh`, 0.23.0): [download](https://hypertemplates.net/downloads/) and put it on your `PATH`; `tools/build.sh` downloads it into `.bin/` if it can't find it. The extras need Python 3 and Pillow (`requirements.txt`, which Cloudflare installs).

## How the site is built

| Piece | Where |
|---|---|
| Site settings, nav menu, `rel="me"` links | `site.yaml` (available in layouts as `site.*`) |
| Pages | `content/**/index.md`: one folder per page. `ugly_url: true` makes `content/now/index.md` `/now.html` instead of `/now/` |
| Layouts | `layouts/<name>.html`, picked by `layout:` in front matter; whole HTML documents using [HyperTemplates directives](https://hypertemplates.net/docs/reference/core/directives/) (`ht-include`, `ht-if`, `ht-each`, `ht-apply`) |
| Shared pieces | `fragments/site/` (head, title/description/link-preview tags, nav, footer, scripts) and `fragments/blog/` (blog head tags, subnav, one post's body and date, hearts and comments). `fragments/builtin/head_start.html` replaces HyperTemplates' built-in `<head>` tags |
| Template functions | `plugins/*.js`: `datefmt`, `excerpt` (untitled posts' titles and descriptions), `now_cards`, `og_image`, `bare_url` |
| Computed data | `data/blog/posts.js` (`data.blog.posts`: every post, newest first, with its `body`, first `image` and link `preview`; used by every blog page and by the feeds), `data/blog/replies.js` (`data.blog.replies`), `data/home.js` (`data.home`: the home page's front matter, for `/about` and `/contact`) |
| Theme | `theme.json`: this repository is the theme. `assets/` is its static folder, so `assets/stylesheets/x.css` is `/stylesheets/x.css` |
| Everything else | `tools/build.sh` → `tools/build_extras.py` (below) |

HyperTemplates only writes HTML pages and Atom feeds. `tools/build_extras.py` adds the rest:

- before the build, `data/link_previews.json` (gitignored): the preview card under each post with an external link, from the linked page's Open Graph tags;
- after the build, `/blog/feed.xml` (RSS) and `/blog/feed.json`, `/blog/archive/index.json` and `/blog/photos/index.json`, the `.md` copies of the main pages, `/llms.txt`, `/sitemap.xml`, `/.well-known/about.md` and `/.well-known/contact.vcf`, and the link-preview cards.

It reads page data with `hyperctl cms data inspect`, so it always sees the same posts, dates and HTML as the layouts.

Templating notes, for anyone editing layouts:

- Plugins work in `ht-apply` text and attributes, but not in `ht-if` or `ht-each`, and calls can't be nested. Values a condition needs are computed in `data/blog/posts.js` instead.
- In an `ht-each` element with an `ht-if` ("only some items"), its children are filled in before the condition is checked, so optional values there need a fallback: `${ post.image, "" }`.
- Elements inside an `ht-each` need their own `ht-apply` for `${ … }` (only the loop element's own text is filled in automatically).
- HTML comments in layouts and fragments end up in the pages, so there are none; notes like these live here.
- On the home page, the Elsewhere icons are two loops (web links, then email): keep Email last in `content/index.md`.

## Editing

| To change | Edit | Generated |
|---|---|---|
| Home links, bio, socials | `content/index.md` | `/`, `/index.md`, `/about`, `/contact`, `/.well-known/about.md`, `/.well-known/contact.vcf` |
| Now | `content/now/index.md`: plain Markdown, one `## Heading` + list per card (icons in front matter); bump `updated_at` | `/now.html`, `/now.md` |
| Resume | `content/resume/index.md` | `/resume.html`, `/resume.md` |
| Blogroll | Replace `data/blogroll.opml` with a NetNewsWire export (`static/blogroll.opml` is a link to it); bump `updated_at` in `content/blogroll/index.md` | `/blogroll.html`, `/blogroll.md`, `/blogroll.opml` |
| Site nav | `nav` in `site.yaml` | nav menus, `/llms.txt` page list |
| CSS and JS | `assets/stylesheets/`, `assets/js/` | `/stylesheets/`, `/js/`; links carry `?v=<commit>`, so browsers never use a stale copy |
| Static files (images, PDF, `human.json`, `CNAME`, `_redirects`, `_headers`) | `static/` | copied as-is |

## Blog

- New post: `tools/new-post.sh <slug>` (or `tools/new-post.sh <slug> "Title"`) creates `content/blog/YYYY/MM/DD/<slug>/index.md`, published at `/blog/YYYY/MM/DD/<slug>.html`. Write below the front matter, push.
- Images: next to the post's `index.md`, referenced by file name (`![alt](photo.jpg)`). Older posts use `static/blog/uploads/YYYY/`, referenced as `/blog/uploads/...`; both work.
- A post is any page under `/blog/` that isn't `unlisted: true` (archive, photos and replies are) or `draft: true`. Posts from a HyperTemplates app (`types/post.yaml`) land at `/blog/<timestamp>/` and show up like any other.
- Feeds: `/blog/feed.xml` (RSS), `/blog/feed.json` and `/blog/atom.xml` (Atom, built by HyperTemplates from `feed` in `content/blog/index.md`). Imported posts keep their Micro.blog `guid` in the RSS and JSON feeds, so readers don't show them again. The RSS feed started from Minimism (MIT, see `tools/LICENSE-minimism`).
- `#hashtags` in posts link to generated tag pages (`/tags/<tag>/`, `layouts/tag.html`).
- Replies: `data/blog/replies_*.json` (Micro.blog export) at `/blog/replies/`.
- `tools/import_microblog.py`: the one-off export cleanup.

## Hearts and comments

- Under each post: a ❤️ button and comments merged from the post's Bluesky and Mastodon copies (`fragments/blog/interactions.html`, `assets/js/interactions.js`). Comments load in the browser from the public Bluesky and Mastodon APIs, using the `bluesky`/`mastodon` front matter of each post. Bluesky accounts that opted out of being shown to logged-out viewers (`!no-unauthenticated`) are skipped, except your own.
- Hearts: `functions/openheart/[[path]].js`, a Cloudflare Pages Function implementing [Open Heart](https://openheart.fyi), backed by the D1 database `juanvisbal-hearts` (bound as `HEARTS`; schema in `migrations/`). One heart per visitor per post per day; only a hash of IP + post + day is stored. Clicking again unhearts: the button sends a random per-browser ID (stored hashed) with the heart, and `DELETE` with that ID removes it (an extension to Open Heart).

## Cross-posting

`.github/workflows/crosspost.yaml` runs `tools/crosspost.py` after each push to `main` that touches `content/blog/`. New posts (`created_at` 2026-10-01 or later, not drafts, not unlisted, not in the future) go to Bluesky (`juanvisbal.com`) and Mastodon (`@juan@social.lol`); the links to those copies are committed back into the post's front matter, which turns on its comments box. Short posts are posted in full; titled posts as title + link; long posts are shortened on Bluesky (300 characters) with a link. Up to 4 images (next to the post or in `static/`), with alt text. Secrets: `BLUESKY_APP_PASSWORD`, `MASTODON_TOKEN`. To test the logins without posting: Actions → "Cross-post new blog posts" → Run workflow → tick "Only check". To see what would be posted, locally: `DRY_RUN=1 python3 tools/crosspost.py`.

It only sees posts committed to this repository. A HyperTemplates app that publishes the built site straight to a host (its `git`/`s3` providers) would skip both this and `tools/build_extras.py`.

## About and contact

- `/about` and `/contact` (`content/about/`, `content/contact/`; `layouts/about.html`, `layouts/contact.html`; `assets/stylesheets/profile.css`): the bio, links and Elsewhere from the home page's front matter (`data.home`, `data/home.js`). Micro.blog's old About and Contact links (`/blog/about/`, `/blog/contact/`) redirect to them (`static/_redirects`).
- Their machine-readable twins:
  - [AboutSpec](https://aboutspec.org/): `/.well-known/about.md`, the bio as `summary` front matter, then the same profile as `/index.md`, linking to the HTML pages. `/about` links to it as its Markdown version (`markdown:` in `content/about/index.md`), so it's also in `/llms.txt`.
  - [ContactSpec](https://contactspec.org/): `/.well-known/contact.vcf`, a vCard 4.0 with the name, nickname (`@juanvisbal.com`), email (the `mailto:` link in `elsewhere`), home page, photo, and the other `elsewhere` links as social profiles. Each profile is written twice: `SOCIALPROFILE` (the vCard 4.0 standard) and `X-SOCIALPROFILE`, the only one Apple's Contacts framework (iOS and macOS apps) reads.
  - Both are written by `tools/build_extras.py` (`about_spec`, `contact_spec`) from the home page's front matter. Their `Content-Type` and CORS headers are set in `static/_headers`.

## Light/dark theme

Colours are tokens in `assets/stylesheets/tokens.css` (`light-dark()`, with a system-preference fallback). The footer button (`fragments/site/footer.html`, `assets/js/theme.js`) toggles between following the system and the opposite theme, stored in `localStorage`; an inline script in `<head>` (`fragments/site/head.html`) applies it before the page renders.

## Link preview cards

Pages and posts without a photo point to a 1200×630 card at `/og/<page path>.png` (`plugins/og_image.js`), drawn after the build by `tools/build_extras.py`: `tools/og/base.png` (background + Memoji) with the page title or post text in JetBrains Mono (`tools/og/fonts/`, SIL Open Font License). Posts with a photo use the photo.
