# Open Source M3U — Hindi / English / Marathi / Punjabi / Urdu

`final_m3u.m3u` is a single IPTV playlist that merges publicly available,
open-source live-TV streams for **Hindi, English, Marathi, Punjabi and
Urdu**, grouped into per-language categories so it's easy to browse in any
IPTV player (VLC, TiviMate, IPTV Smarters, etc.):

```
Hindi Movies      Hindi News        Hindi Entertainment      Hindi Others
English Movies    English News      English Entertainment    English Others
Marathi Movies    Marathi News      Marathi Entertainment    Marathi Others
Punjabi Movies    Punjabi News      Punjabi Entertainment    Punjabi Others
Urdu Movies       Urdu News         Urdu Entertainment       Urdu Others
```

Channels that don't clearly fall under Movies / News / Entertainment are
placed in the language's `Others` group (music, sports, kids, religious,
lifestyle, documentary, general, etc.).

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

## Usage

Point any IPTV player at the raw URL of `final_m3u.m3u` in this repo, or
download it and open it directly in VLC (`Media → Open Network Stream`).
