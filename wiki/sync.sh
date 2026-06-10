#!/usr/bin/env bash
#
# Publish the contents of wiki/ to the GitHub Wiki repository.
#
# By default the wiki remote is derived from this repository's "origin"
# (…/<owner>/<repo>.git -> …/<owner>/<repo>.wiki.git). Override with WIKI_REMOTE.
#
# Usage:
#   bash wiki/sync.sh
#   WIKI_REMOTE=https://github.com/<owner>/<repo>.wiki.git bash wiki/sync.sh
#
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SRC_DIR/.." && pwd)"

# Derive the wiki remote from origin unless explicitly provided.
if [[ -z "${WIKI_REMOTE:-}" ]]; then
  origin="$(git -C "$REPO_DIR" remote get-url origin 2>/dev/null || true)"
  if [[ -n "$origin" ]]; then
    WIKI_REMOTE="${origin%.git}.wiki.git"
  else
    WIKI_REMOTE="https://github.com/hanelias/siamang.wiki.git"
  fi
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "==> Cloning wiki: $WIKI_REMOTE"
if ! git clone --quiet "$WIKI_REMOTE" "$TMP_DIR"; then
  cat >&2 <<'EOF'
ERROR: could not clone the wiki repository.

The wiki must be enabled and initialized first:
  1. Repository Settings -> Features -> enable "Wikis".
  2. Create the first page (Home) once via the GitHub web UI.
Then re-run this script.
EOF
  exit 1
fi

echo "==> Syncing pages"
# Remove existing pages, then copy the current sources (wiki/ is the source of truth).
find "$TMP_DIR" -maxdepth 1 -type f -name '*.md' -delete
cp "$SRC_DIR"/*.md "$TMP_DIR"/
# The folder README is documentation for contributors, not a wiki page.
rm -f "$TMP_DIR"/README.md

cd "$TMP_DIR"
git add -A
if git diff --cached --quiet; then
  echo "==> No changes to publish."
  exit 0
fi
git commit --quiet -m "docs(wiki): sync from siamang/wiki"

echo "==> Pushing"
for attempt in 1 2 3 4; do
  if git push origin HEAD; then
    echo "==> Published to $WIKI_REMOTE"
    exit 0
  fi
  wait=$((2 ** attempt))
  echo "push failed; retrying in ${wait}s ..." >&2
  sleep "$wait"
done
echo "ERROR: push failed after retries." >&2
exit 1
