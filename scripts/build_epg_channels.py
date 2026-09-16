#!/usr/bin/env python3
"""
Builds scripts/epg_channels.xml: a custom channel list (in the format the
iptv-org/epg grabber expects via its --channels option) that maps every
tvg-id currently in final_m3u.m3u to a real EPG source, using the
community-maintained guide mappings from iptv-org/api.

Run this from a machine/CI runner with internet access, before running the
grabber:
    pip install requests
    python3 scripts/build_epg_channels.py
    git clone --depth 1 https://github.com/iptv-org/epg.git epg-tool
    cd epg-tool && npm install
    npm run grab --- --channels=../scripts/epg_channels.xml --output=../epg.xml --maxConnections=10
"""
import os
import re
import sys
import xml.sax.saxutils as sx

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_PATH = os.path.join(ROOT, "final_m3u.m3u")
OUTPUT_PATH = os.path.join(ROOT, "scripts", "epg_channels.xml")
GUIDES_URL = "https://raw.githubusercontent.com/iptv-org/api/gh-pages/guides.json"

# Preferred grabber sites, best coverage/reliability for our channel set first.
SITE_PRIORITY = [
    "tataplay.com",
    "airtelxstream.in",
    "dishtv.in",
    "zee5.com",
    "sky.com",
    "nowplayer.now.com",
    "tvtv.us",
    "i.mjh.nz",
]

LANG_BY_NAME = {
    "Hindi": "hi",
    "English": "en",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Urdu": "ur",
}


def extract_tvg_ids(m3u_path):
    ids = {}  # tvg_id -> lang
    lang = None
    with open(m3u_path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#EXTINF"):
                continue
            m = re.search(r'tvg-id="([^"]*)"', line)
            g = re.search(r'group-title="([^"]*)"', line)
            if not m or not m.group(1):
                continue
            lang_name = g.group(1).split(" ")[0] if g else ""
            ids[m.group(1)] = LANG_BY_NAME.get(lang_name, "en")
    return ids


def site_rank(site):
    return SITE_PRIORITY.index(site) if site in SITE_PRIORITY else len(SITE_PRIORITY)


def main() -> int:
    tvg_ids = extract_tvg_ids(PLAYLIST_PATH)
    print(f"Playlist has {len(tvg_ids)} unique tvg-ids.")

    print("Downloading guide mappings...")
    guides = requests.get(GUIDES_URL, timeout=60).json()
    print(f"Loaded {len(guides)} guide mappings.")

    # Index guide entries by "channel@feed" and by bare "channel".
    by_key = {}
    by_channel = {}
    for g in guides:
        if not g.get("site_id"):
            continue
        key = f"{g['channel']}@{g['feed']}" if g.get("feed") else g["channel"]
        by_key.setdefault(key, []).append(g)
        by_channel.setdefault(g["channel"], []).append(g)

    chosen = {}
    for tvg_id in tvg_ids:
        candidates = by_key.get(tvg_id) or by_channel.get(tvg_id.split("@")[0])
        if not candidates:
            continue
        best = min(candidates, key=lambda g: site_rank(g["site"]))
        chosen[tvg_id] = best

    print(f"Matched {len(chosen)} / {len(tvg_ids)} channels to an EPG source.")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<channels>"]
    for tvg_id in sorted(chosen):
        g = chosen[tvg_id]
        lang = tvg_ids.get(tvg_id, "en")
        name = sx.escape(g.get("site_name") or tvg_id)
        lines.append(
            f'  <channel site="{sx.escape(g["site"])}" '
            f'site_id="{sx.escape(str(g["site_id"]))}" '
            f'lang="{lang}" xmltv_id="{sx.escape(tvg_id)}">{name}</channel>'
        )
    lines.append("</channels>")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
