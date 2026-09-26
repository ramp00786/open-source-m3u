#!/usr/bin/env python3
"""
Adds a curated set of genuinely open-source / public-domain movies (from
archive.org) into scripts/source_channels.json as an on-demand "Movies"
group, alongside the live IPTV channels. Safe to re-run: skips titles
already present, and skips any archive.org identifier that no longer
resolves instead of failing the run.

Run with internet access (this is a CI/runner step, not run in the
sandbox that built this repo):
    pip install requests
    python3 scripts/add_public_domain_movies.py
"""
import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_PATH = os.path.join(ROOT, "scripts", "source_channels.json")

LANG = "Public Domain"
CATEGORY = "Movies"

# Well-known, out-of-copyright films hosted on the Internet Archive.
# (identifier, display title)
TITLES = [
    ("night_of_the_living_dead", "Night of the Living Dead (1968)"),
    ("Nosferatu1922", "Nosferatu (1922)"),
    ("ThePhantomOfTheOpera1925_1", "The Phantom of the Opera (1925)"),
    ("TheGeneral1926", "The General (1926)"),
    ("Sherlock_Jr", "Sherlock Jr. (1924)"),
    ("Metropolis_201410", "Metropolis (1927)"),
    ("his_girl_friday", "His Girl Friday (1940)"),
    ("PlanNineFromOuterSpace", "Plan 9 from Outer Space (1959)"),
    ("DetourNoir1945", "Detour (1945)"),
    ("Charade1963", "Charade (1963)"),
    ("HouseOnHauntedHill1959", "House on Haunted Hill (1959)"),
    ("CarnivalOfSouls1962", "Carnival of Souls (1962)"),
    ("DOA_1950", "D.O.A. (1950)"),
    ("TheLittleShopOfHorrors1960", "Little Shop of Horrors (1960)"),
    ("ChaplinTheKid", "The Kid (1921)"),
]


def find_video_url(identifier):
    r = requests.get(f"https://archive.org/metadata/{identifier}", timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    files = data.get("files") or []
    if not files:
        return None
    mp4s = [f for f in files if (f.get("name") or "").lower().endswith(".mp4")]
    if not mp4s:
        return None
    best = max(mp4s, key=lambda f: int(f.get("size") or 0))
    return f"https://archive.org/download/{identifier}/{best['name']}"


def main() -> int:
    with open(SOURCE_PATH, encoding="utf-8") as f:
        entries = json.load(f)

    existing_tvg_ids = {e.get("tvg_id") for e in entries}
    added = 0

    for identifier, title in TITLES:
        tvg_id = f"pd.{identifier}"
        if tvg_id in existing_tvg_ids:
            continue
        try:
            url = find_video_url(identifier)
        except requests.RequestException:
            url = None
        if not url:
            print(f"skip (no video found): {identifier}")
            continue
        extinf = f'#EXTINF:-1 tvg-id="{tvg_id}" group-title="{LANG} {CATEGORY}",{title}'
        entries.append(
            {
                "lang": LANG,
                "category": CATEGORY,
                "extinf": extinf,
                "url": url,
                "name": title,
                "tvg_id": tvg_id,
            }
        )
        added += 1
        print(f"added: {title} -> {url}")

    with open(SOURCE_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"Added {added} public-domain movies. Total entries: {len(entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
