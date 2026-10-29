#!/bin/sh
# cron entry point on server1 (every 3h): mirror new channel videos for the kiosk, then add
# them to the videos page on birancpa.co.il. The site step runs even if a download failed.
cd "$(dirname "$0")"
echo "=== $(date '+%F %H:%M')"
docker compose --profile fetch run --rm fetch
python3 site_sync.py
