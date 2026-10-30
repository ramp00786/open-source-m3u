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
import collections
import threading
from urllib.parse import urlparse

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PATH = os.path.join(ROOT, "scripts", "source_channels.json")
OUTPUT_PATH = os.path.join(ROOT, "final_m3u.m3u")

LANG_ORDER = ["Hindi", "English", "Marathi", "Punjabi", "Urdu", "Public Domain"]
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
RETRY_TIMEOUT = 25
MAX_WORKERS = 100
PER_HOST = 4
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
}


def is_working(url: str, timeout: int = TIMEOUT):
    try:
        r = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
        )
        try:
            if r.status_code >= 400:
                return False, f"HTTP {r.status_code}"
            ctype = r.headers.get("Content-Type", "").lower()
            if ".m3u8" not in r.url.lower() and "mpegurl" not in ctype:
                return True, "ok"
            # A 200 HTML error page isn't a playable stream: require a real HLS playlist.
            head = b""
            for chunk in r.iter_content(1024):
                head += chunk
                if len(head) >= 2048:
                    break
            if b"#EXTM3U" in head[:2048]:
                return True, "ok"
            return False, "not an HLS playlist"
        finally:
            r.close()
    except requests.RequestException as e:
        return False, type(e).__name__


def main() -> int:
    with open(SOURCE_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    urls = sorted({e["url"] for e in entries})
    print(f"Checking {len(urls)} unique stream URLs...")

    # Small IPTV servers drop connections when dozens of checks hit them at once.
    host_locks = collections.defaultdict(lambda: threading.Semaphore(PER_HOST))

    def check(url, timeout):
        with host_locks[urlparse(url).netloc]:
            return is_working(url, timeout)

    def run(batch, timeout, workers):
        out = {}
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(check, u, timeout): u for u in batch}
            for n, fut in enumerate(cf.as_completed(futures), 1):
                try:
                    out[futures[fut]] = fut.result()
                except Exception as e:
                    out[futures[fut]] = (False, type(e).__name__)
                if n % 250 == 0 or n == len(batch):
                    print(f"  checked {n}/{len(batch)}")
        return out

    results = run(urls, TIMEOUT, MAX_WORKERS)
    failed = [u for u, (ok, _) in results.items() if not ok]
    print(f"Retrying {len(failed)} failed URLs with a longer timeout...")
    retried = run(failed, RETRY_TIMEOUT, 40)
    results.update(retried)
    print(f"Recovered on retry: {sum(ok for ok, _ in retried.values())}")

    by_host = collections.defaultdict(list)
    for u, (ok, reason) in results.items():
        if not ok:
            by_host[urlparse(u).netloc].append(reason)
    print("Hosts with most failures:")
    for host, reasons in sorted(by_host.items(), key=lambda kv: -len(kv[1]))[:15]:
        print(f"  {len(reasons):4}  {host}  {collections.Counter(reasons).most_common(2)}")

    working = [e for e in entries if results.get(e["url"], (False, ""))[0]]
    print(f"Working: {len(working)} / {len(entries)}")

    previous = 0
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            previous = sum(1 for line in f if line.startswith("#EXTINF"))
    if len(working) < previous * 0.5:
        # Likely a runner/network problem, not half the streams dying at once.
        print(f"Refusing to overwrite: only {len(working)} working vs {previous} before.")
        return 1

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
