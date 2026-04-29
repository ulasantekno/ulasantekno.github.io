#!/bin/bash
# Cron wrapper for UlasanTekno auto-blog
# Runs every 5 hours

export HOME=/home/ubuntu
export PATH=/usr/local/bin:/usr/bin:/bin

REPO="/home/ubuntu/ulasantekno-repo"
LOG="/tmp/ulasantekno-cron.log"
PYTHON="/usr/bin/python3.12"

echo "========================================" >> "$LOG"
echo "🚀 Cron started: $(date)" >> "$LOG"
echo "========================================" >> "$LOG"

cd "$REPO" || { echo "❌ Failed to cd $REPO"; exit 1; }

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
