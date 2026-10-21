---
name: land
description: >-
  Land changes on juanvisbal.com (the juanvisbal/juanvisbal.github.io repository): commit them
  to the framework branch (hugo), verify the Cloudflare Pages preview, merge hugo into main, and
  confirm the production deploy. Invoke only when the user has explicitly requested landing or
  merging the changes, not merely for review, preparation, passing checks, or skill installation.
disable-model-invocation: true
metadata:
  delta-action: land
---

# Land changes on juanvisbal.com

Invoking this skill is the request to land. Do not ask whether to merge or say you are waiting
for an explicit landing request; carry out the workflow below. Stop only for the blockers named
here, and when you stop, say plainly that the changes have **not** landed and why.

## Model

- Work happens on the branch named after the site's current framework: **`hugo`** (the site is
  Hugo: `hugo.toml`, `tools/build.sh`). Landing means merging `hugo` into **`main`**, the
  Cloudflare Pages production branch (README.md, first paragraph).
- Publish only to the **`origin`** remote (GitHub, `juanvisbal/juanvisbal.github.io`). Never push
  to `local`. No pull requests: branches are unprotected and changes are pushed directly.
- Commits are signed (`commit.gpgsign` is on, SSH key). Never pass `--no-gpg-sign`,
  `--no-verify`, or force-push either branch.
- Commit style: a plain imperative summary line, then short `-` bullets saying what changed and
  why (see `git log origin/main`).
- Conflicts: resolve automatically when the intended result is clear, always keeping unrelated
  work on both sides (for example a bot commit recording cross-post links next to an unrelated
  edit). Stop and report if the right result is ambiguous, or if the build fails after resolving.

Use non-interactive commands only: prefix `git commit` and `git merge` with `GIT_EDITOR=true` so a
message can never open an editor. For messages, `git commit` takes `-m "<text>"` or `-F -` (reads
stdin); **`git merge` takes only `-m`, never `-F`** — it errors with `could not read file '-'` and
does not merge. Repeat `-m` to add paragraphs.

## 1. Preflight

```sh
git fetch origin
git --no-optional-locks status -sb
git log --oneline origin/main..HEAD
```

Identify the changes to land: uncommitted changes in the checkout and/or local commits not yet
on `origin/main` or `origin/hugo`. Land only the changes this request is about; if unrelated
uncommitted work is present and can't be cleanly separated, stop and ask which files to include.
If there is nothing to land, say so and stop.

## 2. Bring `hugo` up to date

Make local `hugo` match `origin/hugo`:

- No local `hugo`: `git branch hugo origin/hugo`.
- Local `hugo` is an ancestor of `origin/hugo` (stale): `git branch -f hugo origin/hugo` (only when
  `hugo` is not checked out; otherwise `git merge --ff-only origin/hugo` on it).
- Local `hugo` has commits not on `origin/hugo`: those are unpublished work; stop and ask, unless
  they are the very changes being landed.

Then make sure `hugo` contains everything on `origin/main` (cross-post bot commits, anything
pushed straight to `main`). Carry uncommitted changes across the checkout with
`git stash push --include-untracked` / `git stash pop` if needed.

```sh
git switch hugo
git merge --ff-only origin/main || GIT_EDITOR=true git merge origin/main -m "Merge main into hugo"
```

(`--ff-only` succeeds whenever `origin/hugo` is an ancestor of `origin/main`, the usual case after
a previous landing.)

## 3. Put the changes on `hugo`

- Uncommitted changes: `git add` the relevant paths and commit on `hugo` with `-F -` and a
  message in the house style.
- Local commits on another branch (for example `main`): `git cherry-pick <commits>` onto `hugo`,
  then move that branch back to its upstream only if those commits are now on `hugo` and it has
  no other unpublished commits.

## 4. Verify locally

```sh
sh tools/build.sh
```

Source: `tools/build.sh` (the Cloudflare Pages build command, README.md). It needs Hugo 0.167.0
on `PATH` on macOS (it only downloads Hugo on Linux). Output goes to `public/` (gitignored). A
non-zero exit is a blocker. Warnings about unreachable link-preview URLs
(`resources.GetRemote`) are network noise, not failures.

Then spot-check the generated files the change affects, for example `public/.well-known/about.md`,
`contact.vcf`, `following.opml` (valid XML), the changed pages and their `.md` copies,
`public/llms.txt`, and `public/_headers` / `public/_redirects` when `static/` changed.

## 5. Publish `hugo` and wait for its Cloudflare preview

```sh
git push origin hugo
SHA=$(git rev-parse hugo)
gh api repos/juanvisbal/juanvisbal.github.io/commits/$SHA/check-runs \
  --jq '.check_runs[] | [.name, .status, .conclusion, .details_url] | @tsv'
```

Poll (about every 20 s, up to ~10 min) until the **`Cloudflare Pages`** check run for that exact
SHA has `status` `completed` and `conclusion` `success`. Use check runs, not
`commits/<sha>/status`: the combined status reads `pending` with no statuses even after a
successful deploy. If the check is missing after the timeout, pending, or anything other than
`success`, stop: the changes have not landed. Report the check's `details_url`.

## 6. Merge `hugo` into `main`

```sh
git switch main
git merge --ff-only origin/main
GIT_EDITOR=true git merge --no-ff hugo \
  -m "Merge the hugo branch (<short summary>) into main" \
  -m "- <what changed>"
```

The first `-m` is the subject, later ones become body paragraphs separated by blank lines.

If local `main` has commits that are not on `origin/main` and were not moved to `hugo` in step 3,
stop and ask. If the merge brings in nothing new (`main` already contains `hugo`), report that the
changes were already on `main` and go to step 8.

## 7. Push `main`

```sh
git push origin main
```

If the push is rejected because `origin/main` moved (usually the cross-post bot), run
`git fetch origin`, reset local `main` to `origin/main` (`git reset --hard origin/main`, safe here
because the only local commit is the merge just made), redo step 6, rerun `sh tools/build.sh`,
and push again.

## 8. Confirm the landing

```sh
git ls-remote origin refs/heads/main
gh api repos/juanvisbal/juanvisbal.github.io/commits/<main-sha>/check-runs \
  --jq '.check_runs[] | [.name, .status, .conclusion] | @tsv'
```

- `origin/main` must point at the merge commit (or a later commit containing it).
- Wait as in step 5 for the **`Cloudflare Pages`** check run on that SHA (the production deploy)
  to be `completed` / `success`. Anything else means the change is on `main` but not live: report
  that.
- Spot-check the affected live URLs, for example
  `curl -sI https://juanvisbal.com/<path>` for status, `Content-Type`,
  `Access-Control-Allow-Origin`, and redirect `location`, and `curl -s` for changed content.
- If `content/blog/` changed, the "Cross-post new blog posts" workflow
  (`.github/workflows/crosspost.yaml`) runs on that push and commits back to `main`; check it with
  `gh run list -R juanvisbal/juanvisbal.github.io --workflow crosspost.yaml --limit 1` and mention
  it. The next landing picks up its commit in step 2.

Report: the commits landed, the merge SHA on `main`, the check results, and what the live
site returned.
