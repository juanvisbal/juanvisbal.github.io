# juanvisbal.com

Hugo site: the main pages and the blog (`/blog/`, migrated from Micro.blog on 2026-10-08). Built by Cloudflare Pages on every push: build command `bash build.sh`, output directory `public`. `build.sh` pins the Hugo version (the build image default is too old for this site).

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
