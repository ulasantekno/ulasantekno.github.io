#!/bin/bash
# Cron wrapper for UlasanTekno auto-blog
# Recommended cadence: 1-2 posts/day, not every few hours.

export HOME=/home/ubuntu
export PATH=/usr/local/bin:/usr/bin:/bin

REPO="/home/ubuntu/.openclaw/workspace/ulasantekno.github.io"
LOG="$REPO/logs/auto-generate.log"
PYTHON="/usr/bin/python3.12"

mkdir -p "$(dirname "$LOG")"

echo "========================================" >> "$LOG"
echo "🚀 Cron started: $(date)" >> "$LOG"
echo "========================================" >> "$LOG"

cd "$REPO" || { echo "❌ Failed to cd $REPO" >> "$LOG"; exit 1; }

git pull --ff-only origin main >> "$LOG" 2>&1 || {
    echo "❌ git pull failed; aborting to avoid conflicts: $(date)" >> "$LOG"
    exit 1
}

# Run auto-generate script
$PYTHON scripts/auto-generate-post.py >> "$LOG" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Success: $(date)" >> "$LOG"
else
    echo "❌ Failed with exit code $EXIT_CODE: $(date)" >> "$LOG"
fi

echo "" >> "$LOG"
exit $EXIT_CODE
