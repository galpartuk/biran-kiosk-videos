"""Adds new channel videos to the "סרטונים" page on birancpa.co.il (page 1890, Elementor).

Runs on server1 right after fetch.py (see run.sh). fetch.py leaves the whole channel in
media/channel.json; any id that is on neither the videos page nor the media page
("הופעות בתקשורת", 1881) is added. Only adds, never removes or reorders:
  - a landscape video goes to the top, right after the opening pair, two to a row;
  - a Short goes to the bottom of the shortest column of the Shorts grid.
The page's previous Elementor data is kept in site-backups/ before every change.
Python 3 standard library only; talks to WordPress through wp-cli in svc-biranold-site.
"""
import datetime
import json
import os
import re
import secrets
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTAINER = "svc-biranold-site"
WP = ["docker", "exec", CONTAINER, "php", "/tmp/wp", "--allow-root", "--path=/var/www/html"]
PAGE, MEDIA_PAGE = 1890, 1881
MAX_NEW = 8          # more than this in one run means something is off: change nothing
BACKUPS = os.path.join(HERE, "site-backups")
VIMEO, DAILY = "https://vimeo.com/235215203", "https://www.dailymotion.com/video/x6tqhqb"


def wp(*args):
    return subprocess.run(WP + list(args), check=True, capture_output=True, text=True).stdout


def page_data(page):
    return json.loads(wp("post", "meta", "get", str(page), "_elementor_data"))


def ids_in(data):
    text = json.dumps(data)
    return set(re.findall(r"(?:watch\?v=|embed/|youtu\.be/|shorts/)([\w-]{11})", text.replace("\\/", "/")))


def all_ids(data):
    out = set()
    def walk(e):
        out.add(e["id"])
        for c in e.get("elements", []):
            walk(c)
    for e in data:
        walk(e)
    return out


def main():
    try:
        with open(os.path.join(HERE, "media", "channel.json"), encoding="utf-8") as f:
            channel = json.load(f)
    except FileNotFoundError:
        sys.exit("no media/channel.json yet")

    data = page_data(PAGE)
    have = ids_in(data) | ids_in(page_data(MEDIA_PAGE))
    new = [v for v in channel if v["id"] not in have]
    if not new:
        print("site: nothing new")
        return
    if len(new) > MAX_NEW:
        sys.exit(f"site: {len(new)} new videos at once, refusing; check channel.json")

    used = all_ids(data)
    def nid():
        while True:
            i = secrets.token_hex(4)[:7]
            if i not in used:
                used.add(i)
                return i

    def video(vid, tall):
        url = f"https://www.youtube.com/embed/{vid}" if tall else f"https://www.youtube.com/watch?v={vid}"
        return {"id": nid(), "elType": "widget", "widgetType": "video", "elements": [],
                "settings": {"youtube_url": url, "vimeo_url": VIMEO, "dailymotion_url": DAILY}}

    def column(widgets):
        return {"id": nid(), "elType": "column", "isInner": False, "elements": widgets,
                "settings": {"_column_size": 50, "_inline_size": None}}

    # the Shorts grid is the three-column section; everything above it is landscape
    grid = next((s for s in data if s.get("settings", {}).get("structure") == "30"), None)
    if grid is None:
        sys.exit("site: Shorts grid not found on the page, refusing")

    # Landscape videos this script added live in "auto-videos" sections. They are laid out again
    # on every run, newest first, two to a row, so a new video never lands beside an older one.
    auto = [s for s in data if s.get("settings", {}).get("_css_classes") == "auto-videos"]
    widgets = [video(v["id"], False) for v in new if not v["tall"]]   # channel.json is newest first
    widgets += [w for s in auto for c in s["elements"] for w in c["elements"]]
    data[:] = [s for s in data if s not in auto]
    rows = [{"id": nid(), "elType": "section", "isInner": False,
             "settings": {"structure": "20", "_css_classes": "auto-videos"},
             "elements": [column(widgets[i:i + 1]), column(widgets[i + 1:i + 2])]}
            for i in range(0, len(widgets), 2)]
    data[1:1] = rows
    for v in reversed([v for v in new if v["tall"]]):
        min(grid["elements"], key=lambda c: len(c["elements"]))["elements"].append(video(v["id"], True))

    os.makedirs(BACKUPS, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    with open(os.path.join(BACKUPS, f"{PAGE}-{stamp}.json"), "w", encoding="utf-8") as f:
        f.write(wp("post", "meta", "get", str(PAGE), "_elementor_data"))
    for old in sorted(os.listdir(BACKUPS))[:-30]:
        os.remove(os.path.join(BACKUPS, old))

    tmp = os.path.join(HERE, ".site_sync.json")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    php = os.path.join(HERE, ".site_sync.php")
    with open(php, "w", encoding="utf-8") as f:
        f.write("<?php\n$j = file_get_contents('/tmp/site_sync.json');\n"
                "json_decode($j); if (json_last_error()) { echo \"bad json\\n\"; exit(1); }\n"
                f"update_post_meta({PAGE}, '_elementor_data', wp_slash($j));\n"
                f"wp_update_post(['ID' => {PAGE}]);\necho \"ok\\n\";\n")
    subprocess.run(["docker", "cp", tmp, f"{CONTAINER}:/tmp/site_sync.json"], check=True)
    subprocess.run(["docker", "cp", php, f"{CONTAINER}:/tmp/site_sync.php"], check=True)
    try:
        print(wp("eval-file", "/tmp/site_sync.php").strip())
        wp("elementor", "flush-css")
        wp("cache", "flush")
    finally:
        subprocess.run(["docker", "exec", CONTAINER, "rm", "-f", "/tmp/site_sync.json", "/tmp/site_sync.php"])
        os.remove(tmp)
        os.remove(php)
    print("site: added " + ", ".join(v["id"] + (" (short)" if v["tall"] else "") for v in new))


if __name__ == "__main__":
    main()
