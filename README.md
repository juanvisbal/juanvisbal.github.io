# juanvisbal.com

Hugo site: the main pages and the blog (`/blog/`, migrated from Micro.blog on 2026-10-08). Built by Cloudflare Pages on every push (production branch `main`): build command `sh tools/build.sh`, output directory `public`. `tools/build.sh` runs Hugo 0.167.0, downloading it if the build image's Hugo is a different version. (The site ran on HyperTemplates for a day in October 2026; that version is on the `hypertemplates` branch.)

## Local preview

For the full site, including working likes, run:

```sh
sh tools/preview.sh
```

Open http://localhost:8788/blog/2026/10/09/thanks-to-the-nova-im.html to test the feedback row. Click the heart to like, reload to check persistence, then click again to unlike.

Requires Hugo, Node.js, and Wrangler 4 (`npm install -g wrangler@4` if needed). The script applies the existing migrations to a **local-only D1 database**, watches Hugo sources, and runs the real Cloudflare Pages Functions. No Cloudflare login is needed and production likes are untouched. Test data and generated files stay in the ignored `.wrangler/` directory; the migration config (`tools/wrangler.local.toml`) is not used for deployment. Social comments still load from the public Bluesky/Mastodon APIs; replying follows the existing links.

Leave the command running while testing; Ctrl+C stops it. Use `PORT=8789 sh tools/preview.sh` if port 8788 is occupied. Source changes rebuild automatically; refresh the browser to see them.

For a static-only preview, `hugo server` still works at http://localhost:1313, but cannot serve the heart endpoint.

## Editing

| To change | Edit | Generated |
|---|---|---|
| Home links, bio, socials | `content/_index.md` | `/`, `/index.md`, `/.well-known/about.md` (bio), `/.well-known/contact.vcf` |
| About | `content/about.md`: plain Markdown, who you are (no link lists) | `/about.html`, `/about.md`, `/.well-known/about.md` |
| Now | `content/now.md`: plain Markdown, one `## Heading` + list per card (icons in front matter); bump `lastmod` | `/now.html`, `/now.md` |
| Resume | `content/resume.md` | `/resume.html`, `/resume.md` |
| Blogroll | Replace `assets/blogroll.opml` with a NetNewsWire export; folders become category cards; bump `lastmod` in `content/blogroll.md` | `/blogroll.html`, `/blogroll.md`, `/blogroll.opml`, `/.well-known/following.opml` |
| Site nav | `[[menus.main]]` in `hugo.toml` | nav menus, `/llms.txt` page list |
| CSS and JS | `assets/stylesheets/`, `assets/js/` | fingerprinted URLs (`layouts/_partials/site/css.html`, `js.html`), so browsers never use a stale copy |
| Static files (images, PDF, `human.json`, `CNAME`) | `static/` | copied as-is |

## Spacing

`assets/stylesheets/tokens.css` defines the shared vertical rhythm: `--space-small` (0.5rem) for related details, `--space-content` (1rem) for content groups, and `--space-section` (2rem) for sections and dividers. Post, archive, and replies lists share `.divided-list` in `pages.css`: equal padding around interior dividers, with outer spacing owned by the surrounding section instead of doubled at list edges. `.card` (also in `pages.css`) is the shared panel behind the `/now` sections and the blogroll categories.

## Blog

- New post: `hugo new content blog/YYYY/MM/DD/<slug>.md`, write below the front matter, push.
- Images: `static/blog/uploads/YYYY/`, referenced as `/blog/uploads/...`.
- Feeds: `/blog/feed.xml` and `/blog/feed.json`. Imported posts keep their Micro.blog `guid`, so readers don't show them again.
- Design: the blog uses the main site's layout (`layouts/baseof.html`) and stylesheets, plus `assets/stylesheets/blog.css`. Templates in `layouts/blog/` apply only to `/blog/`. The feed templates started from Minimism (MIT, see `layouts/blog/LICENSE-minimism`).
- Replies: `data/blog/replies_*.json` (Micro.blog export) at `/blog/replies/`, each row tagged with the network it came from (`layouts/_partials/blog/reply-network.html`); Mastodon replies load live via `assets/js/replies.js` from the `mastodon` account in `content/blog/replies.md`.
- `tools/import_microblog.py`: the one-off export cleanup.

## Hearts and comments

- Under each post: a ❤️ button and links to reply on the post's Bluesky and Mastodon copies (`layouts/_partials/blog/interactions.html`, `assets/js/interactions.js`). Their replies load in the browser from the public APIs, using the `bluesky`/`mastodon` front matter of each post. The Comments heading and list appear only when replies exist; failures still show a status message. Bluesky accounts that opted out of being shown to logged-out viewers (`!no-unauthenticated`) are skipped, except your own.
- Hearts: `functions/openheart/[[path]].js`, a Cloudflare Pages Function implementing [Open Heart](https://openheart.fyi), backed by the D1 database `juanvisbal-hearts` (bound as `HEARTS`; schema in `migrations/`). One heart per visitor per post per day; only a hash of IP + post + day is stored. Clicking again unhearts: the button sends a random per-browser ID (stored hashed) with the heart, and `DELETE` with that ID removes it (an extension to Open Heart).

## Cross-posting

`.github/workflows/crosspost.yaml` runs `tools/crosspost.py` after each push to `main` that touches `content/blog/`. New posts (dated 2026-10-01 or later, not drafts, not in the future) go to Bluesky (`juanvisbal.com`) and Mastodon (`@juan@social.lol`). With /dev/null configured, posts dated 2026-10-21 or later also go there; older posts aren't backfilled. Each successful copy is committed back into the post's front matter (`bluesky`, `mastodon`, `devnull`) and skipped on later runs. A network's failure doesn't prevent posting to the others, and successful copies are saved even if another network fails. The comments box uses the Bluesky and Mastodon copies only.

Short posts are posted in full; titled posts as title + link. Long posts are shortened with a link on Bluesky (300 characters) and /dev/null (4,000 characters). Up to 4 images with alt text on Bluesky/Mastodon; up to 3 on /dev/null, whose CLI doesn't accept alt text. JPEG, PNG and WebP are supported on /dev/null; GIFs are converted to JPEG, as are oversized images.

### Credentials

- Bluesky: repository Actions secret `BLUESKY_APP_PASSWORD`.
- Mastodon: repository Actions secret `MASTODON_TOKEN` (`write:statuses`, `write:media`).
- /dev/null (optional): sign in at https://dev-null.sh with GitHub first. Generate a **dedicated, unencrypted Ed25519 key** outside this repository, add its **public** key to that GitHub account under **Settings → SSH and GPG keys → New SSH key** (Authentication Key), and put its **private** key in the repository Actions secret `DEVNULL_SSH_KEY`. Don't reuse a personal login/deploy key or commit either key. The workflow loads the secret into a temporary SSH agent and removes it on exit; only the public key is written to a temporary file. If the secret is absent, /dev/null is skipped without affecting the other networks.

/dev/null uses the SSH-signed CLI protocol at https://dev-null.sh/commit: only the public key, signed payload, signature and attached images are sent. Text and image payloads use their respective signing namespaces. A pending-review copy is recorded too, so it isn't submitted again while moderation is pending.

To test the configured logins and signing without posting: Actions → **Cross-post new blog posts** → **Run workflow** → tick **Only check**. Locally, load the dedicated key into `ssh-agent` and set `DEVNULL_PUBLIC_KEY` to the path of its `.pub` file. `DRY_RUN=1 python3 tools/crosspost.py` previews eligible posts on all three networks without credentials, posting or front-matter changes. Run regression tests with `python3 -m unittest discover -s tools -p 'test_*.py'`.

## SocialSpec: about, contact, and following

The site implements the three [SocialSpec](https://socialspec.org/) APIs, so feed readers and social apps can show a full profile from three `GET` requests:

- [AboutSpec](https://aboutspec.org/): `/.well-known/about.md` (`layouts/home.aboutspec.md`), who you are: the bio as `summary` front matter, then "### About Juan" and the About page's text (`content/about.md`). No link lists or contact details: those belong in `contact.vcf`.
- [ContactSpec](https://contactspec.org/): `/.well-known/contact.vcf` (`layouts/home.contactspec.vcf`), a vCard 4.0 with the name, nickname (`@juanvisbal.com`), email (the `mailto:` link in `elsewhere`), home page, photo, and the other `elsewhere` links as social profiles. Each profile is written twice: `SOCIALPROFILE` (the vCard 4.0 standard) and `X-SOCIALPROFILE`, the only one Apple's Contacts framework (iOS and macOS apps) reads.
- [FollowSpec](https://followspec.org/): `/.well-known/following.opml` (`layouts/home.following.opml`), the blogroll as an OPML 2.0 subscription list (`layouts/_partials/site/following.opml`). `/blogroll.opml` is the same file.
- About is generated from `content/about.md` and the bio, contact from `content/_index.md`, following from `assets/blogroll.opml` (output formats in `hugo.toml`). Their `Content-Type` and CORS headers are set in `static/_headers`.
- SocialSpec starts from a feed: `/feed.xml` and `/feed.json` redirect to the blog's feeds (`static/_redirects`).

## Light/dark theme

Colours are tokens in `assets/stylesheets/tokens.css` (`light-dark()`, with a system-preference fallback). The footer button (`layouts/_partials/site/theme-toggle.html`, `assets/js/theme.js`) cycles **System → Light → Dark → System**. Light and Dark are saved in `localStorage`; System removes the override and follows OS changes automatically. The button's tooltip and accessible name describe the current preference and next action. An inline script in `<head>` applies a saved override before the page renders; other open tabs stay in sync.

Theme regression tests: `node --test tools/theme.test.cjs` (no extra dependencies).

## Shared layout pieces

`layouts/_partials/site/`: `head-common.html` (theme setup, favicons, feeds, stylesheet), `nav.html` (breadcrumb + menu), `page-header.html` (title, `note` from front matter, optional intro/subnav), `footer.html` (with the theme toggle), `scripts.html`, `css.html`/`js.html` (fingerprinted assets).

## Link preview cards

Pages and posts without a photo get a generated 1200×630 card (`layouts/_partials/site/og-card.html`): `assets/og/base.png` (background + Memoji) with the page title or post text in JetBrains Mono (`assets/fonts/`, SIL Open Font License). Posts with a photo use the photo.
