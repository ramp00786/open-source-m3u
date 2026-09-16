#!/usr/bin/env python3
"""
Adds/refreshes the url-tvg / x-tvg-url attributes on the #EXTM3U line of
final_m3u.m3u so IPTV players auto-load epg.xml for program guide data.
Only runs if epg.xml was actually produced by the grabber step.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLIST_PATH = os.path.join(ROOT, "final_m3u.m3u")
EPG_PATH = os.path.join(ROOT, "epg.xml")
EPG_URL = "https://raw.githubusercontent.com/ramp00786/open-source-m3u/main/epg.xml"


def main() -> int:
    if not os.path.exists(EPG_PATH) or os.path.getsize(EPG_PATH) == 0:
        print("epg.xml missing/empty, leaving final_m3u.m3u header as-is.")
        return 0

    with open(PLAYLIST_PATH, encoding="utf-8") as f:
        lines = f.readlines()

    if not lines or not lines[0].startswith("#EXTM3U"):
        print("final_m3u.m3u has no #EXTM3U header, skipping.")
        return 0

    lines[0] = f'#EXTM3U url-tvg="{EPG_URL}" x-tvg-url="{EPG_URL}"\n'

    with open(PLAYLIST_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"Set EPG header to {EPG_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
