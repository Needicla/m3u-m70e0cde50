#!/usr/bin/env python3
"""
Build a personal Pluto TV (US) M3U playlist.

Replaces every shared https://jmp2.uk/plu-<id>.m3u8 link with a direct Pluto
stitcher URL that uses a session token minted for that one channel.

No third-party dependencies.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

SOURCE = "https://raw.githubusercontent.com/BuddyChewChew/app-m3u-generator/main/playlists/plutotv_us.m3u"
OUTPUT = "pluto_us.m3u"

# A US residential-ish address, so the token Pluto issues claims a US location.
XFF = "185.236.200.172"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)

HEADERS = {
    "origin": "https://pluto.tv",
    "referer": "https://pluto.tv/",
    "user-agent": UA,
    "accept": "*/*",
    "X-Forwarded-For": XFF,
}

WORKERS = 6
RETRIES = 4


def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers={"user-agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def mint(channel_id):
    client_id = str(uuid.uuid4())
    params = {
        "appName": "web",
        "appVersion": "8.1.0",
        "deviceVersion": "133.0.0",
        "deviceModel": "web",
        "deviceMake": "chrome",
        "deviceType": "web",
        "clientID": client_id,
        "clientModelNumber": "1.0.0",
        "serverSideAds": "false",
        "architecture": "x86_64",
        "buildVersion": "1.0.0",
        "drmCapabilities": "widevine:L3",
    }
    url = "https://boot.pluto.tv/v4/start?" + urllib.parse.urlencode(params)

    last_error = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
            token = data.get("sessionToken")
            stitcher = data.get("stitcherParams")
            if not token:
                raise RuntimeError("no sessionToken in response")
            return (
                "https://ipv4.pluto.tv/api/tn/video/playout/v2/stitch/hls/channel/"
                f"{channel_id}/master.m3u8?{stitcher}&jwt={token}"
                "&quality=720p&deviceMake=chrome&deviceType=web&deviceModel=web"
                "&deviceVersion=133.0.0&architecture=x86_64&buildVersion=1.0.0"
                "&includeExtendedEvents=true&masterJWTPassthrough=true"
            )
        except Exception as exc:  # noqa: BLE001 - we want every failure retried
            last_error = exc
            time.sleep(1.5 * (attempt + 1))

    print(f"  ! {channel_id}: {last_error}", flush=True)
    return None


def main():
    print(f"Downloading {SOURCE}", flush=True)
    text = fetch_text(SOURCE)
    lines = text.splitlines()

    channel_ids = []
    for line in lines:
        line = line.strip()
        if line.startswith("https://jmp2.uk/plu-") and line.endswith(".m3u8"):
            cid = line[len("https://jmp2.uk/plu-") : -len(".m3u8")]
            if cid not in channel_ids:
                channel_ids.append(cid)

    print(f"Channels to resolve: {len(channel_ids)}", flush=True)

    resolved = {}
    failures = 0
    done = 0

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(mint, cid): cid for cid in channel_ids}
        for future in as_completed(futures):
            cid = futures[future]
            url = future.result()
            if url:
                resolved[cid] = url
            else:
                failures += 1
            done += 1
            if done % 25 == 0 or done == len(channel_ids):
                print(f"  {done}/{len(channel_ids)} (failures: {failures})", flush=True)

    if not resolved:
        print("ERROR: every channel failed, refusing to write an empty playlist", flush=True)
        return 1

    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("https://jmp2.uk/plu-") and stripped.endswith(".m3u8"):
            cid = stripped[len("https://jmp2.uk/plu-") : -len(".m3u8")]
            # Keep the original shared link as a per-channel fallback.
            out.append(resolved.get(cid, stripped))
        else:
            out.append(line)

    with open(OUTPUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")

    print(f"Wrote {OUTPUT}: {len(resolved)} direct links, {failures} fallbacks", flush=True)
    return 0 if failures < len(channel_ids) * 0.5 else 2


if __name__ == "__main__":
    sys.exit(main())
