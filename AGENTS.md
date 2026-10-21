# Development workflow

- Use `hugo` for development work, not `main`. Check the current branch before editing.
- If another branch is checked out, preserve any existing work before switching to `hugo`.
- Commit completed, validated changes on `hugo` so they survive branch switches.
- `main` is the production branch. Merge or push to it only when the user explicitly authorizes landing the specific change.
- The Hearts endpoint and schema (`functions/openheart/[[path]].js`, `migrations/000[12]_*.sql`) are vendored verbatim from the private `juanvisbal/openheart-d1` repo. Change them there, then run `python3 tools/sync-hearts.py --sync`; `python3 tools/sync-hearts.py` fails when the copies have drifted.
