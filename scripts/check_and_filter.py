#!/usr/bin/env python3
"""
Validates every stream URL in scripts/source_channels.json and writes
final_m3u.m3u containing only channels whose stream URL responded
successfully at check time, grouped as "<Language> <Category>".

Source channel data comes from the iptv-org/database and iptv-org/iptv
open-source projects (https://github.com/iptv-org/iptv), filtered down to
Hindi, English, Marathi, Punjabi and Urdu channels.

Run this from a machine/CI runner with normal internet access:
    pip install requests
    python3 scripts/check_and_filter.py
"""
import json
import os
import re
import sys
import concurrent.futures as cf

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PATH = os.path.join(ROOT, "scripts", "source_channels.json")
OUTPUT_PATH = os.path.join(ROOT, "final_m3u.m3u")

LANG_ORDER = ["Hindi", "English", "Marathi", "Punjabi", "Urdu"]
CATEGORY_ORDER = [
    "Movies",
    "News",
    "Entertainment",
    "Music",
    "Kids",
    "Devotional",
    "Sports",
    "Education",
    "Documentary",
    "Business",
    "Others",
]

TIMEOUT = 12
MAX_WORKERS = 40
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
}


def is_working(url: str) -> bool:
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
        ok = r.status_code < 400
        r.close()
        return ok
    except requests.RequestException:
        return False


def main() -> int:
    with open(SOURCE_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    urls = sorted({e["url"] for e in entries})
    print(f"Checking {len(urls)} unique stream URLs...")

    results = {}
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {ex.submit(is_working, u): u for u in urls}
        done = 0
        for fut in cf.as_completed(futures):
            u = futures[fut]
            try:
                results[u] = fut.result()
            except Exception:
                results[u] = False
            done += 1
            if done % 25 == 0 or done == len(urls):
                print(f"  checked {done}/{len(urls)}")

    working = [e for e in entries if results.get(e["url"])]
    print(f"Working: {len(working)} / {len(entries)}")

    def sort_key(e):
        lang_idx = LANG_ORDER.index(e["lang"]) if e["lang"] in LANG_ORDER else 99
        cat_idx = (
            CATEGORY_ORDER.index(e["category"])
            if e["category"] in CATEGORY_ORDER
            else 99
        )
        return (lang_idx, cat_idx, e["name"])

    working.sort(key=sort_key)

    lines = ["#EXTM3U"]
    counts = {}
    for e in working:
        group = f'{e["lang"]} {e["category"]}'
        counts[group] = counts.get(group, 0) + 1
        extinf = e["extinf"]
        # Rewrite group-title to our own "<Language> <Category>" grouping.
        if 'group-title="' in extinf:
            extinf = re.sub(r'group-title="[^"]*"', f'group-title="{group}"', extinf)
        else:
            extinf = extinf.replace("#EXTINF:-1", f'#EXTINF:-1 group-title="{group}"', 1)
        lines.append(extinf)
        lines.append(e["url"])

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\nChannels per group:")
    for lang in LANG_ORDER:
        for cat in CATEGORY_ORDER:
            g = f"{lang} {cat}"
            if g in counts:
                print(f"  {g}: {counts[g]}")

    print(f"\nWrote {OUTPUT_PATH} with {len(working)} working channels.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
