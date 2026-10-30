# Pluto TV (US) â€” personal playlist

A GitHub Action rebuilds `pluto_us.m3u` every 6 hours with **your own** Pluto
session tokens, instead of the shared `jmp2.uk` token that everyone else uses.

That shared token is the reason the channels freeze or return 403: `jmp2.uk`
caches one token per channel for 24 hours and hands it to every viewer. This
repo mints a fresh token per channel instead.

## Playlist URL

Add this to any player (VLC, TiviMate, OTT Navigator, Kodi, Jellyfin, â€¦):

```
https://raw.githubusercontent.com/Needicla/m3u-m70e0cde50/main/pluto_us.m3u
```

It never changes. The Action refreshes the tokens inside it.

## How it works

1. `generate.py` downloads the channel metadata from
   `BuddyChewChew/app-m3u-generator` (names, logos, groups, EPG ids, 433 US
   channels).
2. For each channel it mints a Pluto web session (`boot.pluto.tv/v4/start`)
   and builds the direct stitcher URL:
   `https://ipv4.pluto.tv/.../channel/<id>/master.m3u8?<params>&jwt=<token>`
3. If a channel fails, the original `jmp2.uk` link is kept as a fallback for
   that channel only.
4. `.github/workflows/update.yml` runs every 6 hours, commits `pluto_us.m3u`
   if it changed, and pushes.

Tokens last 24 hours, so a run every 6 hours leaves a wide safety margin.

## Manual refresh

Actions tab â†’ **Update Pluto TV (US) playlist** â†’ **Run workflow**.

Or from a terminal:

```bash
gh workflow run update.yml --repo Needicla/m3u-m70e0cde50
```

## Run it locally

```bash
python generate.py
```

Writes `pluto_us.m3u` in the current directory. No dependencies beyond the
Python standard library.

## Notes

- **Public repo**: the raw URL needs to be public for a player to fetch it
  without credentials, so anyone with the link can use these tokens. In
  practice that is just you, which is what matters here.
- **Delay**: GitHub's scheduler can start a run 10â€“60 minutes late. Not an
  issue with 24-hour tokens.
- **Cache**: `raw.githubusercontent.com` can serve a cached copy for a few
  minutes after a commit. Players that re-read the playlist on a schedule
  will pick up changes on their own.
- **US only**. The token mint sends a US `X-Forwarded-For` header, so Pluto
  geolocates the session to the US.
- **Small history**. `pluto_us.m3u` is about 1.4 MB of unique tokens, so a new
  commit every 6 hours would add over a gigabyte a year. The Action therefore
  amends a single data commit and force-pushes `main`, which keeps the repo at
  two commits: the code and the current playlist.
