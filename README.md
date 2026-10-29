# biran-kiosk-videos

Video feed for the entrance tablet at Shabtai Biran CPA. **Since 2026-10-29 the feed lives on
server1** at https://kiosk-videos.all-good.co.il/videos.json (`/opt/services/kiosk-videos`, files in
`media/`, setup in `server/`). A cron job runs `fetch.py` there every 3 hours (log in `fetch.log`).
It checks the firm's YouTube channel and copies any new video (mp4 + thumbnails) into `media/`
along with an updated `videos.json`. The tablet polls that file and downloads what it lacks.
The same run (`server/run.sh`) then calls `server/site_sync.py`, which adds any new channel video to
the "סרטונים" page on birancpa.co.il (page 1890). It only adds, skips videos already on "הופעות בתקשורת"
(1881) or hidden in `overrides.json`, and saves the page's previous data in `site-backups/` first.
The `media` release here now only holds a `videos.json` with `moved_to`, which sends the tablet
to the server. The old laptop scheduled task "Biran kiosk videos" is disabled.

To update the server copy: `tar -c fetch.py overrides.json -C server Dockerfile docker-compose.yml site_sync.py run.sh | ssh azizi@all-good.co.il "tar -x -C /opt/services/kiosk-videos"`,
then `docker compose --profile fetch build fetch` there.

- Fix a title or category, cut a long video short in the loop, or hide a video: edit
  `overrides.json`, e.g. `{"yBjn1cn2e90": {"title": "...", "cat": "tax"}, "abc": {"hidden": true}}`.
  Categories: `office`, `tax`, `media`, `digital`. Applied on the next run once copied to the server (or run `docker compose --profile fetch run --rm fetch` there).
- To run it by hand: `python fetch.py` on a PC with yt-dlp, ffmpeg and an authenticated `gh`.
- To move the feed elsewhere, add `"moved_to": "<new videos.json URL>"` to the current `videos.json`.
