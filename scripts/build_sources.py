#!/usr/bin/env python3
"""
Rebuilds scripts/source_channels.json from the latest open-source playlists:
- iptv-org per-language playlists (Hindi, English, Marathi, Punjabi, Urdu)
- iptv-org country feeds for India and Pakistan (language/category looked
  up in iptv-org/database)
- Free-TV/IPTV India, UK and USA playlists

Entries are de-duplicated by URL. Nothing here is checked for liveness;
check_and_filter.py does that afterwards.
"""
import csv
import io
import json
import os
import re
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(ROOT, "scripts", "source_channels.json")

RAW = "https://raw.githubusercontent.com"
LANG_FILES = [
    ("Hindi", "hin"),
    ("Marathi", "mar"),
    ("Punjabi", "pan"),
    ("Urdu", "urd"),
    ("English", "eng"),
]
LANG_CODES = {code: name for name, code in LANG_FILES}
COUNTRY_FEEDS = ["in", "pk"]
FREE_TV = [("india", None), ("uk", "English"), ("usa", "English")]

SONY_SPORTS = re.compile(r"\bsony\s*(sports|ten|six)\b", re.I)

CATEGORY_KEYWORDS = [
    ("movie", "Movies"),
    ("cinema", "Movies"),
    ("film", "Movies"),
    ("news", "News"),
    ("sport", "Sports"),
    ("music", "Music"),
    ("kids", "Kids"),
    ("animation", "Kids"),
    ("cartoon", "Kids"),
    ("religious", "Devotional"),
    ("bhakti", "Devotional"),
    ("aastha", "Devotional"),
    ("sanskar", "Devotional"),
    ("entertainment", "Entertainment"),
    ("education", "Education"),
    ("documentary", "Documentary"),
    ("business", "Business"),
]


def fetch(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def parse_m3u(text):
    entries, extinf = [], None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            extinf = line
        elif line and not line.startswith("#") and extinf:
            entries.append((extinf, line))
            extinf = None
    return entries


def attr(extinf, name):
    m = re.search(rf'{name}="([^"]*)"', extinf)
    return m.group(1) if m else ""


def title(extinf):
    return extinf.split(",", 1)[1].strip() if "," in extinf else ""


def category_of(*texts):
    blob = " ".join(t for t in texts if t).lower()
    for keyword, bucket in CATEGORY_KEYWORDS:
        if keyword in blob:
            return bucket
    return "Others"


def norm(name):
    name = re.sub(r"\(.*?\)|\[.*?\]", "", name.lower())
    name = re.sub(r"\bhd\b", "", name)
    return re.sub(r"[^a-z0-9]", "", name)


def load_database():
    base = f"{RAW}/iptv-org/database/master/data"
    channels = list(csv.DictReader(io.StringIO(fetch(f"{base}/channels.csv"))))
    feeds = csv.DictReader(io.StringIO(fetch(f"{base}/feeds.csv")))
    cats = {c["id"]: c["categories"] for c in channels}
    langs = {}
    for f in feeds:
        langs.setdefault(f["channel"], set()).update(
            l for l in f["languages"].split(";") if l
        )
    by_name = {}
    for c in channels:
        for n in [c["name"]] + c["alt_names"].split(";"):
            if n:
                by_name.setdefault(norm(n), c["id"])
    return cats, langs, by_name


def lang_of(channel_id, langs):
    found = langs.get(channel_id, set())
    for name, code in LANG_FILES:
        if code in found:
            return name
    return None


def keep(name, tvg_id, group):
    if "xxx" in group.lower():
        return False
    # Geo-blocked outside India won't play for viewers in India even if CI can reach it.
    if "[Geo-blocked]" in name and ".in@" not in tvg_id and not tvg_id.endswith(".in"):
        return False
    return True


def main() -> int:
    cats, langs, by_name = load_database()
    out, seen = [], set()

    def add(lang, category, extinf, url, name, tvg_id):
        if url in seen:
            return
        if SONY_SPORTS.search(name):
            lang, category = "Hindi", "Sports"
        seen.add(url)
        out.append(
            {
                "lang": lang,
                "category": category,
                "extinf": extinf,
                "url": url,
                "name": name,
                "tvg_id": tvg_id,
            }
        )

    for lang, code in LANG_FILES:
        text = fetch(f"{RAW}/iptv-org/iptv/gh-pages/languages/{code}.m3u")
        for extinf, url in parse_m3u(text):
            name, tvg_id, group = title(extinf), attr(extinf, "tvg-id"), attr(extinf, "group-title")
            if keep(name, tvg_id, group):
                add(lang, category_of(group), extinf, url, name, tvg_id)

    for cc in COUNTRY_FEEDS:
        text = fetch(f"{RAW}/iptv-org/iptv/master/streams/{cc}.m3u")
        for extinf, url in parse_m3u(text):
            name, tvg_id = title(extinf), attr(extinf, "tvg-id")
            base = tvg_id.split("@")[0]
            lang = lang_of(base, langs)
            if not lang or not keep(name, tvg_id, cats.get(base, "")):
                continue
            add(lang, category_of(cats.get(base, ""), name), extinf, url, name, tvg_id)

    for country, default_lang in FREE_TV:
        text = fetch(f"{RAW}/Free-TV/IPTV/master/playlists/playlist_{country}.m3u8")
        for extinf, url in parse_m3u(text):
            name = title(extinf)
            channel_id = by_name.get(norm(name), "")
            lang = lang_of(channel_id, langs) or default_lang
            if not lang:
                continue
            tvg_id = channel_id
            clean = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{tvg_id}"', extinf)
            add(lang, category_of(cats.get(channel_id, ""), name), clean, url, name, tvg_id)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    counts = {}
    for e in out:
        counts[e["lang"]] = counts.get(e["lang"], 0) + 1
    print(f"Wrote {len(out)} candidate entries: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
