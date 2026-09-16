# Open Source M3U — Hindi / English / Marathi / Punjabi / Urdu

`final_m3u.m3u` is a single IPTV playlist that merges publicly available,
open-source live-TV streams for **Hindi, English, Marathi, Punjabi and
Urdu**, grouped into per-language categories so it's easy to browse in any
IPTV player (VLC, TiviMate, IPTV Smarters, etc.):

Each of Hindi, English, Marathi, Punjabi and Urdu is split into:

```
Movies · News · Entertainment · Music · Kids · Devotional · Sports · Education · Documentary · Business · Others
```

e.g. `Hindi Music`, `Hindi Kids`, `Hindi Devotional`, `Hindi Sports`,
`English Sports`, `English News`, etc. A channel's category comes from its
source group-title (movie/news/sport/music/kids/religious/entertainment/
education/documentary/business keywords, checked in that priority order for
channels tagged with more than one category). Whatever doesn't match any of
these keywords (general, culture, lifestyle, legislative, classic, travel,
weather, etc.) lands in the language's `Others` group.

## Source data

Channel metadata and stream links are sourced from the
[iptv-org/iptv](https://github.com/iptv-org/iptv) and
[iptv-org/database](https://github.com/iptv-org/database) open-source
projects — the largest community-maintained collection of public IPTV
streams. `scripts/source_channels.json` is the frozen candidate list pulled
from their generated per-language playlists (`languages/hin.m3u`,
`eng.m3u`, `mar.m3u`, `pan.m3u`, `urd.m3u`), with English narrowed down to
Indian channels plus well-known international news channels (BBC News, Sky
News, Al Jazeera English, France 24, CGTN, Euronews, CNBC, Bloomberg, DW,
NHK World, TRT World, etc.) to keep it relevant instead of pulling in
thousands of unrelated regional channels from every country.

**Haryanvi** was requested but is not included: there is no genuine
Haryanvi-language broadcast channel in the open-source database (Haryana
state news channels broadcast in Hindi). If you know of a real Haryanvi
stream, add it to `scripts/source_channels.json` and it will be picked up.

## Only working links

Free IPTV stream links go down/change constantly, so "working" is checked
automatically rather than by a one-time manual pass:

- `scripts/check_and_filter.py` requests every stream URL and keeps only
  the ones that respond successfully, then writes `final_m3u.m3u`.
- `.github/workflows/update-playlist.yml` runs this script daily (and on
  demand via **Actions → Update playlist → Run workflow**) and commits the
  refreshed `final_m3u.m3u` straight to this branch, so the file always
  reflects streams that were live at the last check.

To run the check yourself:

```bash
pip install requests
python3 scripts/check_and_filter.py
```

## EPG (program guide)

`epg.xml` is an XMLTV program guide covering as many of the playlist's
channels as have a real, no-login public EPG source (mostly via
`tataplay.com`, `airtelxstream.in` and `dishtv.in`, resolved automatically
from [iptv-org/api](https://github.com/iptv-org/api)'s `guides.json`
channel↔source mapping). `final_m3u.m3u`'s `#EXTM3U` line points at it via
`url-tvg`/`x-tvg-url`, so any player that reads those attributes (VLC,
TiviMate, IPTV Smarters, etc.) loads the guide automatically — nothing to
configure by hand. Channels with no matching source (smaller/local
channels) simply won't show program data, same as before.

Regenerated daily by the same workflow, in order:

1. `scripts/check_and_filter.py` → `final_m3u.m3u` (working links)
2. `scripts/build_epg_channels.py` → `scripts/epg_channels.xml` (maps each
   `tvg-id` still in the playlist to a site + site-specific channel id)
3. the [iptv-org/epg](https://github.com/iptv-org/epg) grabber, run against
   that channel list → `epg.xml`
4. `scripts/add_epg_header.py` stamps the `url-tvg`/`x-tvg-url` attributes
   onto `final_m3u.m3u`

To run it yourself:

```bash
pip install requests
python3 scripts/check_and_filter.py
python3 scripts/build_epg_channels.py
git clone --depth 1 https://github.com/iptv-org/epg.git epg-tool
cd epg-tool && npm install
npm run grab --- --channels=../scripts/epg_channels.xml --output=../epg.xml --maxConnections=10
cd .. && python3 scripts/add_epg_header.py
```

## Usage

Point any IPTV player at the raw URL of `final_m3u.m3u` in this repo, or
download it and open it directly in VLC (`Media → Open Network Stream`).
