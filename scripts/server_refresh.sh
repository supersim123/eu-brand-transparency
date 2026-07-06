#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p "$ROOT_DIR/logs"
exec >> "$ROOT_DIR/logs/server_refresh.log" 2>&1

echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') EU Brand Transparency refresh ==="
git pull --ff-only origin main
python scripts/validate_data.py
python scripts/generate_readme.py

if git diff --quiet -- README.md latest-changes.md data; then
  echo "No generated changes to commit."
  exit 0
fi

git add README.md latest-changes.md data
git commit -m "Update EU Brand Transparency list"
git push origin main
