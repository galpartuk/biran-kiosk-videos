"""Mirrors new videos from the firm's YouTube channel into this repo's "media" release.

The entrance tablet (biran-kiosk) polls videos.json in that release and downloads whatever
it does not have yet. Runs on a schedule in GitHub Actions, and can be run by hand anywhere
with yt-dlp, ffmpeg and an authenticated gh CLI:  python fetch.py

videos.json is the only state: a video listed there is already uploaded. Videos that ship
inside the APK (BUNDLED) are never mirrored. overrides.json fixes a title or category, sets
a loop cut-off ("end", seconds) or hides a video ("hidden": true), keyed by YouTube id.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

CHANNEL = "UCijVSjqTk_ZksU7KjZyF6Mw"
REPO = os.environ.get("GITHUB_REPOSITORY", "galpartuk/biran-kiosk-videos")
TAG = "media"
BASE = f"https://github.com/{REPO}/releases/download/{TAG}/"
HERE = os.path.dirname(os.path.abspath(__file__))

# Already inside the APK (clip01-06, short01-11), as of 2026-10-25.
BUNDLED = {
    "paGrvQuLEQw", "EHDBi4c_WGU", "l7Ck9IiZ4Bw", "vFqw1dS8cBA", "pOlK9b4DoOU", "Kln-hcua6Oc",
    "2JsGgSd9T_c", "6l1Ri_JLYow", "7z4nLQ_XYoA", "FIVlHCtdS8M", "JHUJscWdpt4", "NatW4nTleDU",
    "T0z3jmYUNKg", "a4nbDSCvz9w", "g4Kwst3mOoI", "oniQYMqcDCE", "otYjXDSycg4",
}
# Same keys as CATS in the kiosk's index.html; first match wins, "office" otherwise.
CAT_WORDS = [
    ("digital", ["אפליקצי", "דיגיטל", "אונליין"]),
    ("media", ["כנסת", "ועדת", "ראיון", "אולפן", "חדשות", "ערוץ", "רדיו"]),
    ("tax", ["מס ", "מסים", "מיסים", "מע\"מ", "מע״מ", "עוסק", "רשות", "ניכוי", "החזר"]),
]
LOOP_CUT = 120      # long landscape videos leave the loop after this many seconds
LONG = 180


def run(*cmd, capture=False):
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, check=True, text=True, encoding="utf-8",
                       stdout=subprocess.PIPE if capture else None)
    return r.stdout if capture else None


def channel_ids():
    """Every video and Short on the channel, newest first (per tab)."""
    ids = []
    for tab in ("videos", "shorts"):
        out = run("yt-dlp", "--flat-playlist", "--print", "id",
                  f"https://www.youtube.com/channel/{CHANNEL}/{tab}", capture=True)
        ids += [i.strip() for i in out.splitlines() if i.strip()]
    return ids


def current_manifest():
    try:
        with urllib.request.urlopen(BASE + "videos.json", timeout=30) as r:
            return json.load(r)
    except Exception as e:
        print("no manifest yet:", e)
        return {"version": 1, "videos": []}


def tidy_title(info):
    t = re.sub(r"#\S+", "", info["title"]).split("|")[0].strip(" ,-")
    # "שבתאי בירן חלק 2" says nothing on a card; the description's first line usually does
    desc = (info.get("description") or "").strip().splitlines()
    if re.search(r"חלק\s*\d+\s*$", t) and desc and 4 <= len(desc[0]) <= 70:
        t = desc[0].strip()
    return t[:70]


def guess_cat(text):
    for cat, words in CAT_WORDS:
        if any(w in text for w in words):
            return cat
    return "office"


def mmss(sec):
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def mirror(vid, work):
    """Downloads one video, makes its thumbnails, uploads all three files; returns its entry."""
    url = f"https://www.youtube.com/watch?v={vid}"
    # H.264 + AAC in MP4: what the tablet's WebView plays reliably. 1080p is plenty.
    run("yt-dlp", "-f", "bv*[vcodec^=avc1][height<=1080]+ba[acodec^=mp4a]/b[ext=mp4]",
        "--merge-output-format", "mp4", "--write-info-json", "--no-playlist",
        "-o", os.path.join(work, "%(id)s.%(ext)s"), url)
    mp4 = os.path.join(work, vid + ".mp4")
    with open(os.path.join(work, vid + ".info.json"), encoding="utf-8") as f:
        info = json.load(f)
    w, h, dur = info.get("width") or 16, info.get("height") or 9, info.get("duration") or 0
    tall = h > w

    # Card thumbnail is always 640x360; a tall video also gets a 180x320 poster for the player.
    thumb = os.path.join(work, vid + ".jpg")
    at = str(min(2.0, dur / 3)) if dur else "1"
    run("ffmpeg", "-loglevel", "error", "-y", "-ss", at, "-i", mp4, "-frames:v", "1", "-q:v", "3",
        "-vf", "scale=640:360:force_original_aspect_ratio=increase,crop=640:360", thumb)
    files = [mp4, thumb]
    entry = {
        "id": vid,
        "title": tidy_title(info),
        "cat": guess_cat(info["title"] + " " + (info.get("description") or "")),
        "dur": mmss(dur),
        "tall": tall,
        "date": info.get("upload_date", ""),
        "mp4": vid + ".mp4",
        "thumb": vid + ".jpg",
        "size": os.path.getsize(mp4),
    }
    if tall:
        poster = os.path.join(work, vid + "-tall.jpg")
        run("ffmpeg", "-loglevel", "error", "-y", "-ss", at, "-i", mp4, "-frames:v", "1", "-q:v", "3",
            "-vf", "scale=180:320:force_original_aspect_ratio=increase,crop=180:320", poster)
        files.append(poster)
        entry["poster"] = vid + "-tall.jpg"
    elif dur > LONG:
        entry["end"] = LOOP_CUT
    run("gh", "release", "upload", TAG, *files, "--clobber", "-R", REPO)
    return entry


def main():
    with open(os.path.join(HERE, "overrides.json"), encoding="utf-8") as f:
        overrides = json.load(f)
    manifest = current_manifest()
    have = {v["id"]: v for v in manifest["videos"]}
    hidden = {k for k, o in overrides.items() if o.get("hidden")}

    ids = channel_ids()
    new = [i for i in ids if i not in have and i not in BUNDLED and i not in hidden]
    print(f"{len(ids)} on the channel, {len(have)} mirrored, {len(new)} new")

    failed = []
    with tempfile.TemporaryDirectory() as work:
        for vid in new:
            try:
                have[vid] = mirror(vid, work)
            except subprocess.CalledProcessError as e:
                print(f"!! {vid} failed: {e}", file=sys.stderr)
                failed.append(vid)

    # Channel order (newest first), with manual fixes applied; hidden ones drop out of the list
    # and the tablet deletes its copy.
    order = {v: n for n, v in enumerate(ids)}
    videos = []
    for v in sorted(have.values(), key=lambda v: order.get(v["id"], len(order))):
        o = overrides.get(v["id"], {})
        if o.get("hidden"):
            continue
        videos.append({**v, **{k: o[k] for k in ("title", "cat", "end") if k in o}})
    out = {"version": 1, "base": BASE, "videos": videos}
    if "moved_to" in manifest:
        out["moved_to"] = manifest["moved_to"]

    if out != manifest:
        path = os.path.join(tempfile.gettempdir(), "videos.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        run("gh", "release", "upload", TAG, path, "--clobber", "-R", REPO)
        print(f"videos.json updated: {len(videos)} videos")
    else:
        print("nothing changed")
    if failed:
        sys.exit(f"could not mirror: {', '.join(failed)}")


if __name__ == "__main__":
    main()
