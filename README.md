# biran-kiosk-videos

Video feed for the entrance tablet at Shabtai Biran CPA. Every 3 hours `fetch.py` checks the
firm's YouTube channel, and uploads any new video (mp4 + thumbnails) to the `media` release
together with an updated `videos.json`. The tablet polls that file and downloads what it lacks.

- Fix a title or category, cut a long video short in the loop, or hide a video: edit
  `overrides.json`, e.g. `{"yBjn1cn2e90": {"title": "...", "cat": "tax"}, "abc": {"hidden": true}}`.
  Categories: `office`, `tax`, `media`, `digital`. Applied on the next run (or run the workflow by hand).
- If YouTube blocks the GitHub runners, run `python fetch.py` on a PC with yt-dlp, ffmpeg and `gh`.
- To move the feed elsewhere, add `"moved_to": "<new videos.json URL>"` to the current `videos.json`.
