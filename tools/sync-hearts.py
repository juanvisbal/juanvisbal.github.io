"""Keep the Hearts endpoint and schema identical to the openheart-d1 repo.

Those files are canonical in juanvisbal/openheart-d1. That repo is private, so a Pages
build cannot clone it, and this repo therefore carries verbatim copies. Edit them there,
then run this from the repo root:

    python3 tools/sync-hearts.py --sync      # copy them in and record their hashes
    python3 tools/sync-hearts.py             # check the copies still match the record

The source clone is $OPENHEART_D1, or ../openheart-d1 next to this repo, or --source.
"""

import argparse
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

FILES = (
    "functions/openheart/[[path]].js",
    "migrations/0001_hearts.sql",
    "migrations/0002_heart_visitors.sql",
)
LOCK = pathlib.Path("tools/hearts.lock")
ROOT = pathlib.Path(__file__).resolve().parent.parent


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lock(root):
    """-> (source commit or None, {path: hash})"""
    source, hashes = None, {}
    for line in (root / LOCK).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("source "):
            source = line.split(None, 1)[1]
            continue
        digest, path = line.split(None, 1)
        hashes[path.strip()] = digest
    return source, hashes


def write_lock(root, source_dir):
    commit = git(source_dir, "rev-parse", "--short", "HEAD") or "unknown"
    lines = [
        "# Files vendored from juanvisbal/openheart-d1. Written by tools/sync-hearts.py.",
        f"source {commit}",
    ]
    lines += [f"{sha256(root / name)}  {name}" for name in FILES]
    (root / LOCK).write_text("\n".join(lines) + "\n")


def git(repo, *args):
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def check(root):
    _, hashes = read_lock(root)
    problems = [
        name
        for name in FILES
        if name not in hashes or sha256(root / name) != hashes[name]
    ]
    if problems:
        print("These vendored files differ from tools/hearts.lock:", file=sys.stderr)
        for name in problems:
            print(f"  {name}", file=sys.stderr)
        print(
            "\nMake the change in juanvisbal/openheart-d1, then run:\n"
            "  python3 tools/sync-hearts.py --sync",
            file=sys.stderr,
        )
        return 1
    print(f"{len(FILES)} vendored files match tools/hearts.lock")
    return 0


def sync(root, source_dir):
    missing = [name for name in FILES if not (source_dir / name).exists()]
    if missing:
        print(f"{source_dir} is not an openheart-d1 clone; missing:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1

    dirty = git(source_dir, "status", "--porcelain")
    if dirty:
        print(f"warning: {source_dir} has uncommitted changes; vendoring them anyway", file=sys.stderr)

    for name in FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_dir / name, root / name)
    write_lock(root, source_dir)
    commit = git(source_dir, "rev-parse", "--short", "HEAD") or "unknown"
    print(f"Copied {len(FILES)} files from {source_dir} @ {commit}")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sync", action="store_true", help="copy from the source clone")
    parser.add_argument("--source", type=pathlib.Path, help="openheart-d1 clone to copy from")
    args = parser.parse_args()

    source = args.source or (pathlib.Path(os.environ["OPENHEART_D1"]) if "OPENHEART_D1" in os.environ else None)
    if not args.sync:
        return check(ROOT)

    source = (source or ROOT.parent / "openheart-d1").resolve()
    return sync(ROOT, source)


if __name__ == "__main__":
    sys.exit(main())
