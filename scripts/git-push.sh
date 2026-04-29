#!/bin/bash
# Script otomatisasi push ke GitHub Pages UlasTekno
# Usage: ./scripts/git-push.sh "pesan commit"

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

# Load token dari .env
if [ -f "$REPO_DIR/.env" ]; then
    export $(grep -v '^#' "$REPO_DIR/.env" | xargs)
fi

if [ -z "$GH_TOKEN" ]; then
    echo "❌ GH_TOKEN tidak ditemukan. Pastikan file .env sudah dibuat."
    exit 1
fi

MSG="${1:-"update: auto-commit $(date '+%Y-%m-%d %H:%M')"}"

echo "📦 Menambahkan perubahan..."
git add -A

if git diff --cached --quiet; then
    echo "✅ Tidak ada perubahan untuk di-commit."
    exit 0
fi

echo "📝 Commit: $MSG"
git commit -m "$MSG"

echo "🚀 Push ke GitHub..."
git push "https://${GH_TOKEN}@github.com/ulasantekno/ulasantekno.github.io.git" main

echo "✅ Berhasil dipush! GitHub Pages akan rebuild dalam beberapa menit."
