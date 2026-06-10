#!/usr/bin/env python3
"""
Streamer Web App
================
Brandable control + visualizer UI served on :8081.

- Real-time audio (RMS for VU meters + FFT for spectrum) read from MPD's FIFO
- Now-playing state polled from MPD
- Transport + volume control via REST
- All state pushed to browser clients via WebSocket at 30 Hz

Branding is read at runtime from /etc/streamer/brand.conf (JSON). Edit that
file to white-label the UI for any OEM / customer / DAC manufacturer.
"""

import asyncio
import json
import os
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
from aiohttp import ClientSession, ClientTimeout, WSMsgType, web
from mpd import MPDClient

# ─── Config ───────────────────────────────────────────────────────────────────
FIFO_PATH       = "/tmp/mpd.fifo"
SAMPLE_RATE     = 44100
CHANNELS        = 2
FFT_SIZE        = 2048
NUM_BANDS       = 32
BROADCAST_HZ    = 30
HTTP_PORT       = 8081
MPD_HOST        = "127.0.0.1"
MPD_PORT        = 6600
STATIC_DIR      = Path("/opt/streamer-webapp/static")
BRAND_FILE      = Path("/etc/streamer/brand.conf")
FAVORITES_FILE  = Path("/var/lib/streamer/favorites.json")
THEME_FILE      = Path("/etc/streamer/theme.conf")
RB_MIRRORS      = [
    "https://de1.api.radio-browser.info",
    "https://fi1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://all.api.radio-browser.info",
]
RB_USER_AGENT   = "xAMP-Streamer/1.0"

# ─── Curated audiophile featured stations ─────────────────────────────────────
# Hand-picked, all hi-fi friendly. Mix of FLAC, MP3 320, AAC.
FEATURED_STATIONS = [
    # ── Radio Paradise (the audiophile gold standard) ────────────────────────
    {"name": "Radio Paradise — Main Mix",   "url": "http://stream.radioparadise.com/flac",
     "homepage": "https://radioparadise.com", "favicon": "https://radioparadise.com/favicon.ico",
     "codec": "FLAC", "bitrate": 850, "tags": "eclectic,curated,audiophile",
     "country": "US", "language": "english", "description": "Eclectic, listener-supported, hi-res FLAC"},
    {"name": "Radio Paradise — Mellow Mix", "url": "http://stream.radioparadise.com/mellow-flac",
     "homepage": "https://radioparadise.com", "favicon": "https://radioparadise.com/favicon.ico",
     "codec": "FLAC", "bitrate": 850, "tags": "ambient,acoustic,jazz,audiophile",
     "country": "US", "language": "english", "description": "Mellow, contemplative, FLAC"},
    {"name": "Radio Paradise — Rock Mix",   "url": "http://stream.radioparadise.com/rock-flac",
     "homepage": "https://radioparadise.com", "favicon": "https://radioparadise.com/favicon.ico",
     "codec": "FLAC", "bitrate": 850, "tags": "rock,classic-rock,audiophile",
     "country": "US", "language": "english", "description": "Rock-leaning eclectic, FLAC"},
    {"name": "Radio Paradise — Global Mix", "url": "http://stream.radioparadise.com/global-flac",
     "homepage": "https://radioparadise.com", "favicon": "https://radioparadise.com/favicon.ico",
     "codec": "FLAC", "bitrate": 850, "tags": "world,global,audiophile",
     "country": "US", "language": "english", "description": "World music, FLAC"},

    # ── Linn Records (Scottish hi-fi label) ──────────────────────────────────
    {"name": "Linn Jazz",     "url": "http://radio.linnrecords.com/cast/tunein.php/jazz/playlist.pls",
     "homepage": "https://www.linnrecords.com/linn-radio.aspx", "favicon": "",
     "codec": "MP3", "bitrate": 320, "tags": "jazz,audiophile",
     "country": "UK", "language": "english", "description": "Jazz from the Linn Records label"},
    {"name": "Linn Classical","url": "http://radio.linnrecords.com/cast/tunein.php/classical/playlist.pls",
     "homepage": "https://www.linnrecords.com/linn-radio.aspx", "favicon": "",
     "codec": "MP3", "bitrate": 320, "tags": "classical,audiophile",
     "country": "UK", "language": "english", "description": "Classical from the Linn Records label"},
    {"name": "Linn Radio",    "url": "http://radio.linnrecords.com/cast/tunein.php/radio/playlist.pls",
     "homepage": "https://www.linnrecords.com/linn-radio.aspx", "favicon": "",
     "codec": "MP3", "bitrate": 320, "tags": "eclectic,audiophile",
     "country": "UK", "language": "english", "description": "Eclectic mix from Linn Records"},

    # ── Naim ─────────────────────────────────────────────────────────────────
    {"name": "Naim Radio",    "url": "http://mscp3.live-streams.nl:8250/class-flac.flac",
     "homepage": "https://www.naimaudio.com", "favicon": "",
     "codec": "FLAC", "bitrate": 1100, "tags": "classical,audiophile",
     "country": "UK", "language": "english", "description": "Naim Audio's curated classical FLAC stream"},
    {"name": "Naim Jazz",     "url": "http://mscp3.live-streams.nl:8250/jazz-flac.flac",
     "homepage": "https://www.naimaudio.com", "favicon": "",
     "codec": "FLAC", "bitrate": 1100, "tags": "jazz,audiophile",
     "country": "UK", "language": "english", "description": "Naim Audio's curated jazz FLAC stream"},

    # ── BBC ──────────────────────────────────────────────────────────────────
    {"name": "BBC Radio 3",     "url": "http://as-hls-ww-live.akamaized.net/pool_904/live/ww/bbc_radio_three/bbc_radio_three.isml/bbc_radio_three-audio%3d320000.norewind.m3u8",
     "homepage": "https://www.bbc.co.uk/sounds/play/live:bbc_radio_three", "favicon": "",
     "codec": "AAC", "bitrate": 320, "tags": "classical,arts",
     "country": "UK", "language": "english", "description": "BBC's classical music station"},
    {"name": "BBC Radio 6 Music", "url": "http://as-hls-ww-live.akamaized.net/pool_904/live/ww/bbc_6music/bbc_6music.isml/bbc_6music-audio%3d320000.norewind.m3u8",
     "homepage": "https://www.bbc.co.uk/sounds/play/live:bbc_6music", "favicon": "",
     "codec": "AAC", "bitrate": 320, "tags": "alternative,indie",
     "country": "UK", "language": "english", "description": "BBC's alternative music station"},

    # ── France ───────────────────────────────────────────────────────────────
    {"name": "France Musique", "url": "http://icecast.radiofrance.fr/francemusique-hifi.aac",
     "homepage": "https://www.radiofrance.fr/francemusique", "favicon": "",
     "codec": "AAC", "bitrate": 192, "tags": "classical,jazz",
     "country": "FR", "language": "french", "description": "France's classical & jazz station"},
    {"name": "FIP",            "url": "http://icecast.radiofrance.fr/fip-hifi.aac",
     "homepage": "https://www.radiofrance.fr/fip", "favicon": "",
     "codec": "AAC", "bitrate": 192, "tags": "eclectic,jazz,world",
     "country": "FR", "language": "french", "description": "Legendary eclectic French station"},

    # ── SomaFM (San Francisco's commercial-free indie radio empire) ──────────
    {"name": "SomaFM Drone Zone",   "url": "https://ice1.somafm.com/dronezone-256-mp3",
     "homepage": "https://somafm.com/dronezone/", "favicon": "https://somafm.com/img3/dronezone-200.jpg",
     "codec": "MP3", "bitrate": 256, "tags": "ambient,drone,electronic",
     "country": "US", "language": "english", "description": "Atmospheric ambient space music"},
    {"name": "SomaFM Groove Salad", "url": "https://ice1.somafm.com/groovesalad-256-mp3",
     "homepage": "https://somafm.com/groovesalad/", "favicon": "https://somafm.com/img3/groovesalad-200.jpg",
     "codec": "MP3", "bitrate": 256, "tags": "downtempo,ambient,chill",
     "country": "US", "language": "english", "description": "Chilled plastic grooves"},
    {"name": "SomaFM Indie Pop Rocks","url": "https://ice1.somafm.com/indiepop-256-mp3",
     "homepage": "https://somafm.com/indiepop/", "favicon": "https://somafm.com/img3/indiepop-200.jpg",
     "codec": "MP3", "bitrate": 256, "tags": "indie,pop,rock",
     "country": "US", "language": "english", "description": "New and classic indie pop"},
    {"name": "SomaFM Deep Space One","url": "https://ice1.somafm.com/deepspaceone-128-mp3",
     "homepage": "https://somafm.com/deepspaceone/", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "ambient,electronic,space",
     "country": "US", "language": "english", "description": "Deep ambient electronic & space music"},
    {"name": "SomaFM Lush",         "url": "https://ice1.somafm.com/lush-128-mp3",
     "homepage": "https://somafm.com/lush/", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "lush,vocal,downtempo",
     "country": "US", "language": "english", "description": "Sensuous and mellow female vocals"},

    # ── Audiophile Baroque & Classical ───────────────────────────────────────
    {"name": "Venice Classic Radio Italia", "url": "http://174.36.206.197:8000/stream",
     "homepage": "http://www.veniceclassicradio.eu/", "favicon": "",
     "codec": "MP3", "bitrate": 320, "tags": "classical,baroque",
     "country": "IT", "language": "italian", "description": "Italian classical music station"},
    {"name": "Klassik Radio Pure", "url": "http://stream.klassikradio.de/klassikradiopure/mp3-192/internetradio/",
     "homepage": "https://www.klassikradio.de", "favicon": "",
     "codec": "MP3", "bitrate": 192, "tags": "classical",
     "country": "DE", "language": "german", "description": "German classical music"},

    # ── Jazz ─────────────────────────────────────────────────────────────────
    {"name": "Jazz24",          "url": "https://live.amperwave.net/manifest/jazz24-jazz24mp3-ibc1.m3u8",
     "homepage": "https://www.jazz24.org/", "favicon": "",
     "codec": "AAC", "bitrate": 96, "tags": "jazz,smooth-jazz",
     "country": "US", "language": "english", "description": "24-hour jazz from Seattle"},
    {"name": "WBGO 88.3 Newark","url": "https://wbgo.streamguys1.com/wbgo128",
     "homepage": "https://www.wbgo.org/", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "jazz,blues",
     "country": "US", "language": "english", "description": "America's premier jazz public radio station"},

    # ── ABC (Australian Broadcasting Corporation) ────────────────────────────
    {"name": "ABC Jazz",        "url": "https://live-radio01.mediahubaustralia.com/2LRW/aac/",
     "homepage": "https://www.abc.net.au/jazz", "favicon": "",
     "codec": "AAC", "bitrate": 64, "tags": "jazz",
     "country": "AU", "language": "english", "description": "ABC Australia's jazz network"},
    {"name": "ABC Classic",     "url": "https://live-radio01.mediahubaustralia.com/2FMW/aac/",
     "homepage": "https://www.abc.net.au/classic", "favicon": "",
     "codec": "AAC", "bitrate": 64, "tags": "classical",
     "country": "AU", "language": "english", "description": "ABC Australia's classical network"},

    # ── Electronic / Modern ──────────────────────────────────────────────────
    {"name": "KEXP 90.3 Seattle", "url": "https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
     "homepage": "https://www.kexp.org/", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "indie,eclectic",
     "country": "US", "language": "english", "description": "Where the music matters"},
    {"name": "WFMU Freeform",   "url": "http://stream2.wfmu.org/freeform-128k",
     "homepage": "https://wfmu.org/", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "freeform,eclectic",
     "country": "US", "language": "english", "description": "America's most legendary freeform station"},

    # ── Audiophile Specials ──────────────────────────────────────────────────
    {"name": "HD Radio Audiophile Baroque", "url": "http://hd.lagrosseradio.info:8500/lagrosseradio-baroque-128.mp3",
     "homepage": "http://www.lagrosseradio.info", "favicon": "",
     "codec": "MP3", "bitrate": 128, "tags": "baroque,classical",
     "country": "FR", "language": "french", "description": "Dedicated baroque music"},
]


# ─── Caches ──────────────────────────────────────────────────────────────────
class Cache:
    def __init__(self, ttl=300):
        self.ttl = ttl
        self.data = {}
        self.lock = threading.Lock()
    def get(self, key):
        with self.lock:
            if key in self.data:
                value, exp = self.data[key]
                if time.time() < exp:
                    return value
                del self.data[key]
        return None
    def set(self, key, value):
        with self.lock:
            self.data[key] = (value, time.time() + self.ttl)

rb_cache = Cache(ttl=300)


# ─── radio-browser.info client ───────────────────────────────────────────────
async def rb_request(path, params=None):
    """GET /json/<path> from radio-browser.info, trying mirrors."""
    cache_key = f"{path}?{json.dumps(params, sort_keys=True) if params else ''}"
    cached = rb_cache.get(cache_key)
    if cached is not None:
        return cached

    timeout = ClientTimeout(total=10)
    headers = {"User-Agent": RB_USER_AGENT, "Accept": "application/json"}
    mirrors = list(RB_MIRRORS)
    random.shuffle(mirrors)

    async with ClientSession(timeout=timeout, headers=headers) as session:
        for mirror in mirrors:
            url = f"{mirror}/json/{path}"
            try:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        rb_cache.set(cache_key, data)
                        return data
            except Exception as e:
                print(f"[rb] {mirror} failed: {e}", file=sys.stderr)
                continue
    return []


def normalize_station(s):
    """Convert a radio-browser station record to our slimmer schema."""
    return {
        "name":     s.get("name", "").strip(),
        "url":      s.get("url_resolved") or s.get("url", ""),
        "homepage": s.get("homepage", ""),
        "favicon":  s.get("favicon", ""),
        "codec":    s.get("codec", ""),
        "bitrate":  s.get("bitrate", 0) or 0,
        "tags":     s.get("tags", ""),
        "country":  s.get("country", ""),
        "language": s.get("language", ""),
        "votes":    s.get("votes", 0) or 0,
        "clickcount": s.get("clickcount", 0) or 0,
        "stationuuid": s.get("stationuuid", ""),
    }


# ─── Favorites ───────────────────────────────────────────────────────────────
favorites_lock = threading.Lock()

def load_favorites():
    try:
        with open(FAVORITES_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_favorites(data):
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FAVORITES_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(FAVORITES_FILE)


# ─── Cover art for active station ────────────────────────────────────────────
class CoverState:
    def __init__(self):
        self.lock = threading.Lock()
        self.url  = ""
        self.name = ""

cover_state = CoverState()


def set_cover_for_station(station):
    with cover_state.lock:
        cover_state.url  = station.get("favicon") or ""
        cover_state.name = station.get("name") or ""



# ─── Theme presets ───────────────────────────────────────────────────────────
# Each theme defines a complete colour palette consumed by both web UI and
# touchscreen. Both surfaces read these via /api/themes / /api/themes/active.
THEMES = {
    "synthwave": {
        "label":     "Synthwave",
        "tagline":   "Neon · vaporwave · 2080",
        "bg_deep":   "#08051a",
        "bg_mid":    "#16092e",
        "bg_card":   "#1a1230",
        "accent":    "#ff4ecd",
        "accent_2":  "#4edcff",
        "ivory":     "#f5e8d0",
        "ivory_2":   "#d8d0e8",
        "text_1":    "#e8e0f0",
        "text_2":    "#9a8eb0",
        "text_3":    "#5a4f70",
        "spec_top":  "#ffe76b",
        "spec_mid":  "#ff4ecd",
        "spec_bot":  "#5a2a8c",
    },
    "vintage": {
        "label":     "Vintage Hi-Fi",
        "tagline":   "Cream · brass · 1972",
        "bg_deep":   "#0c0805",
        "bg_mid":    "#16110a",
        "bg_card":   "#1c1611",
        "accent":    "#d4a850",
        "accent_2":  "#e8b454",
        "ivory":     "#f5e8d0",
        "ivory_2":   "#e8dcc0",
        "text_1":    "#e8dcc0",
        "text_2":    "#988570",
        "text_3":    "#5a5045",
        "spec_top":  "#ffd96b",
        "spec_mid":  "#d4a850",
        "spec_bot":  "#5a3a18",
    },
    "mcintosh": {
        "label":     "McIntosh Blue",
        "tagline":   "Cream face · blue needles · 1949",
        "bg_deep":   "#040614",
        "bg_mid":    "#0a1028",
        "bg_card":   "#101a35",
        "accent":    "#4a7dc8",
        "accent_2":  "#92c8ff",
        "ivory":     "#f5ecd0",
        "ivory_2":   "#dde0ec",
        "text_1":    "#dde0ec",
        "text_2":    "#7d8aaa",
        "text_3":    "#4a536a",
        "spec_top":  "#cfe6ff",
        "spec_mid":  "#4a7dc8",
        "spec_bot":  "#152a55",
    },
    "aurora": {
        "label":     "Aurora",
        "tagline":   "Northern lights · emerald · violet",
        "bg_deep":   "#02060a",
        "bg_mid":    "#031420",
        "bg_card":   "#082030",
        "accent":    "#3aebb1",
        "accent_2":  "#9a4ed8",
        "ivory":     "#f0fff5",
        "ivory_2":   "#cfeae5",
        "text_1":    "#cfeae5",
        "text_2":    "#6a9890",
        "text_3":    "#3a5650",
        "spec_top":  "#a8ffc8",
        "spec_mid":  "#3aebb1",
        "spec_bot":  "#0a3a4a",
    },
    "tron": {
        "label":     "Tron",
        "tagline":   "Pure black · electric blue",
        "bg_deep":   "#000000",
        "bg_mid":    "#020812",
        "bg_card":   "#08121e",
        "accent":    "#00d8ff",
        "accent_2":  "#ffffff",
        "ivory":     "#ffffff",
        "ivory_2":   "#cfe8f0",
        "text_1":    "#cfe8f0",
        "text_2":    "#5a8090",
        "text_3":    "#2a4050",
        "spec_top":  "#ffffff",
        "spec_mid":  "#00d8ff",
        "spec_bot":  "#003848",
    },
}
DEFAULT_THEME = "synthwave"


def load_active_theme():
    """Read the currently selected theme name. Returns the theme dict."""
    name = DEFAULT_THEME
    try:
        with open(THEME_FILE) as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("name") in THEMES:
            name = data["name"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    theme = dict(THEMES[name])
    theme["name"] = name
    return theme


def save_active_theme(name):
    if name not in THEMES:
        raise ValueError(f"unknown theme: {name}")
    THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = THEME_FILE.with_suffix(".conf.tmp")
    with open(tmp, "w") as f:
        json.dump({"name": name}, f)
    tmp.replace(THEME_FILE)


DEFAULT_BRAND = {
    "sw_name":     "xAMP",
    "sw_subtitle": "AUDIO STREAMER",
    "sw_tagline":  "Bit-Perfect Hi-Fi",
    "hw_name":     "Orchard Audio PecanPi Streamer Ultra",
    "hw_dac":      "Dual Burr-Brown PCM1794A · 130 dB SNR · 24-bit",
    "footer":      "xAMP Audio Streamer · running on Orchard Audio PecanPi",
    "hw_specs": {
        "snr":     "130",
        "dnr":     "125",
        "thd":     "-110",
        "jitter":  "82fs",
    },
}

def load_brand():
    """Read /etc/streamer/brand.conf JSON, merging on top of DEFAULT_BRAND."""
    merged = json.loads(json.dumps(DEFAULT_BRAND))  # deep copy
    try:
        with open(BRAND_FILE) as f:
            data = json.load(f)
        for k, v in data.items():
            if k == "hw_specs" and isinstance(v, dict):
                # Replace, don't merge — brand.conf is the variant's full truth
                # (otherwise legacy DEFAULT_BRAND keys leak through to the UI).
                merged["hw_specs"] = v
            elif isinstance(v, str):
                merged[k] = v
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return merged

# Pink-tilted log-spaced frequency bands
BAND_EDGES   = np.logspace(np.log10(60), np.log10(16000), NUM_BANDS + 1)
BAND_CENTERS = np.sqrt(BAND_EDGES[:-1] * BAND_EDGES[1:])
PINK_TILT    = np.sqrt(BAND_CENTERS / 200.0).astype(np.float32)


# ─── Shared state ─────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        self.lock        = threading.Lock()
        self.l_rms_db    = -60.0
        self.r_rms_db    = -60.0
        self.l_peak_db   = -60.0
        self.r_peak_db   = -60.0
        self.l_peak_t    = 0.0
        self.r_peak_t    = 0.0
        self.spectrum    = np.zeros(NUM_BANDS, dtype=np.float32)
        self.now = {
            "playing":  False,
            "title":    "",
            "artist":   "",
            "album":    "",
            "elapsed":  0.0,
            "duration": 0.0,
            "format":   "",
            "bitrate":  0,
            "volume":   50,
            "source":   "MPD",
        }

state = State()


# ─── FIFO reader thread ───────────────────────────────────────────────────────
def fifo_reader():
    bytes_per_frame = CHANNELS * 2
    bytes_needed    = FFT_SIZE * bytes_per_frame
    pcm_buf         = bytearray()
    fd              = None
    last_data_t     = time.time()

    while True:
        if fd is None:
            try:
                fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
                last_data_t = time.time()
            except FileNotFoundError:
                time.sleep(1.0)
                continue

        chunk = b""
        try:
            chunk = os.read(fd, 16384)
        except BlockingIOError:
            pass
        except OSError:
            try: os.close(fd)
            except: pass
            fd = None
            time.sleep(0.3)
            continue

        now_t = time.time()
        if chunk:
            last_data_t = now_t
            pcm_buf += chunk
            if len(pcm_buf) > bytes_needed * 2:
                pcm_buf = pcm_buf[-bytes_needed * 2:]
        else:
            # No data: if stalled >3s and MPD claims to be playing, the FIFO
            # was likely recreated (e.g. MPD output cycled). Reopen the fd.
            if now_t - last_data_t > 3.0:
                try:
                    if state.now.get("playing"):
                        # Reopen by closing — next loop iteration recreates
                        try: os.close(fd)
                        except: pass
                        fd = None
                        last_data_t = now_t
                        print("[fifo] reopening (stalled while MPD playing)", flush=True)
                except Exception:
                    pass

        if len(pcm_buf) >= bytes_needed:
            tail = bytes(pcm_buf[-bytes_needed:])
            samples = np.frombuffer(tail, dtype=np.int16).astype(np.float32) / 32768.0
            L = samples[0::2]
            R = samples[1::2]

            L_rms_lin = float(np.sqrt(np.mean(L * L)) + 1e-9)
            R_rms_lin = float(np.sqrt(np.mean(R * R)) + 1e-9)
            L_db = max(-60.0, 20.0 * np.log10(L_rms_lin))
            R_db = max(-60.0, 20.0 * np.log10(R_rms_lin))

            mono = (L + R) * 0.5
            window = np.hanning(len(mono))
            spec = np.abs(np.fft.rfft(mono * window))
            freqs = np.fft.rfftfreq(len(mono), 1.0 / SAMPLE_RATE)
            bands = np.zeros(NUM_BANDS, dtype=np.float32)
            for i in range(NUM_BANDS):
                lo, hi = BAND_EDGES[i], BAND_EDGES[i + 1]
                mask = (freqs >= lo) & (freqs < hi)
                if mask.any():
                    bands[i] = spec[mask].mean()
                else:
                    center = (lo + hi) * 0.5
                    nearest = int(np.argmin(np.abs(freqs - center)))
                    bands[i] = spec[nearest]
            bands *= PINK_TILT
            bands = np.log1p(bands * 4.0) / 6.0
            bands = np.clip(bands, 0.0, 1.0)

            with state.lock:
                a = 0.90 if L_db > state.l_rms_db else 0.35
                state.l_rms_db = state.l_rms_db * (1 - a) + L_db * a
                a = 0.90 if R_db > state.r_rms_db else 0.35
                state.r_rms_db = state.r_rms_db * (1 - a) + R_db * a
                if L_db > state.l_peak_db:
                    state.l_peak_db = L_db; state.l_peak_t = now_t
                elif now_t - state.l_peak_t > 1.5:
                    state.l_peak_db = max(-60.0, state.l_peak_db - 0.4)
                if R_db > state.r_peak_db:
                    state.r_peak_db = R_db; state.r_peak_t = now_t
                elif now_t - state.r_peak_t > 1.5:
                    state.r_peak_db = max(-60.0, state.r_peak_db - 0.4)
                state.spectrum = bands
        else:
            with state.lock:
                state.l_rms_db = max(-60.0, state.l_rms_db - 0.6)
                state.r_rms_db = max(-60.0, state.r_rms_db - 0.6)
                state.l_peak_db = max(-60.0, state.l_peak_db - 0.4)
                state.r_peak_db = max(-60.0, state.r_peak_db - 0.4)
                state.spectrum *= 0.92

        time.sleep(1.0 / BROADCAST_HZ)


def mpd_poller():
    global _last_resume_attempt, _resume_backoff_s
    while True:
        c = MPDClient()
        c.timeout = 3
        try:
            c.connect(MPD_HOST, MPD_PORT)
            while True:
                status = c.status()
                song   = c.currentsong()
                with state.lock:
                    state.now["playing"]  = status.get("state") == "play"
                    state.now["title"]    = song.get("title", song.get("name", "")) or ""
                    state.now["artist"]   = song.get("artist", "") or ""
                    state.now["album"]    = song.get("album", "") or ""
                    state.now["elapsed"]  = float(status.get("elapsed", 0) or 0)
                    state.now["duration"] = float(status.get("duration", 0) or 0)
                    state.now["format"]   = status.get("audio", "") or ""
                    state.now["bitrate"]  = int(status.get("bitrate", 0) or 0)
                    state.now["volume"]   = int(status.get("volume", 50) or 50)
                # Auto-resume: if MPD dropped to stop while the user wanted
                # music playing, retry play() — unless AirPlay has the DAC.
                # Uses exponential backoff so we don't hammer a dead stream.
                if status.get("state") == "stop":
                    with _resume_state_lock:
                        should_try = (_user_wants_playing and not _airplay_active)
                        backoff    = _resume_backoff_s
                        last_at    = _last_resume_attempt
                    if should_try:
                        now_t = time.time()
                        if now_t - last_at >= backoff:
                            try:
                                c.play()
                                next_backoff = min(backoff * 2, _RESUME_BACKOFF_MAX)
                                print(f"[mpd] auto-resume: state=stop, retrying play (next backoff={next_backoff}s)",
                                      file=sys.stderr)
                                with _resume_state_lock:
                                    _last_resume_attempt = now_t
                                    _resume_backoff_s = next_backoff
                            except Exception as e:
                                print(f"[mpd] auto-resume play() failed: {e}", file=sys.stderr)
                elif status.get("state") == "play":
                    # Successful playback — reset backoff for next failure
                    with _resume_state_lock:
                        _resume_backoff_s = _RESUME_BACKOFF_MIN
                time.sleep(1.0)
        except Exception as e:
            print(f"[mpd] {e}", file=sys.stderr)
            with state.lock:
                state.now["playing"] = False
            time.sleep(3.0)
        finally:
            try: c.close()
            except: pass


# ─── HTTP / WebSocket handlers ────────────────────────────────────────────────
clients = set()


_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma":        "no-cache",
    "Expires":       "0",
}


async def index(request):
    return web.FileResponse(STATIC_DIR / "index.html", headers=_NO_CACHE_HEADERS)


async def static_handler(request):
    name = request.match_info["name"]
    f = STATIC_DIR / name
    if f.is_file():
        return web.FileResponse(f, headers=_NO_CACHE_HEADERS)
    return web.Response(status=404)


async def brand_handler(request):
    data = load_brand()
    data["theme"] = load_active_theme()
    return web.json_response(data)


async def themes_list(request):
    return web.json_response({
        "themes": [
            {"name": k, "label": v["label"], "tagline": v["tagline"],
             "accent": v["accent"], "accent_2": v["accent_2"], "bg_deep": v["bg_deep"]}
            for k, v in THEMES.items()
        ],
        "active": load_active_theme()["name"],
    })


async def theme_set(request):
    data = await request.json()
    name = data.get("name", "")
    if name not in THEMES:
        return web.json_response({"ok": False, "error": "unknown theme"}, status=400)
    save_active_theme(name)
    return web.json_response({"ok": True, "theme": load_active_theme()})


# ─── Auto-resume state ───────────────────────────────────────────────────────
# Tracks "user wants music playing" intent so the MPD poller can re-issue play
# when the stream drops (TLS errors, 404s, server-side resets) without fighting
# an active AirPlay session.
_resume_state_lock = threading.Lock()
_user_wants_playing = False   # set True after webapp issues a play; False on pause / AirPlay takeover
_airplay_active     = False   # set by shairport-sync hooks via /api/internal/airplay
_last_resume_attempt = 0.0
_resume_backoff_s = 3.0
_RESUME_BACKOFF_MIN = 3.0
_RESUME_BACKOFF_MAX = 30.0


def _set_play_intent(wants_playing: bool):
    """Called by cmd_handler on every play/pause action."""
    global _user_wants_playing, _resume_backoff_s, _last_resume_attempt
    with _resume_state_lock:
        _user_wants_playing = wants_playing
        _resume_backoff_s = _RESUME_BACKOFF_MIN
        _last_resume_attempt = 0.0


def _set_airplay_active(active: bool):
    global _airplay_active, _user_wants_playing
    with _resume_state_lock:
        _airplay_active = active
        if active:
            # AirPlay took over — MPD is no longer the desired source
            _user_wants_playing = False


def _kick_airplay_for_mpd():
    """Ensure shairport-sync isn't holding the DAC before MPD play.
    AirPlay holds ALSA exclusive during active sessions; if the user
    explicitly invokes MPD play through the webapp, that intent wins —
    restart shairport-sync to terminate any active session and free ALSA.
    shairport-sync auto-restarts under systemd within 1-2s, so AirPlay
    is advertising again right after. The connected AirPlay client (if
    any) will need to re-select the device."""
    try:
        subprocess.run(
            ["sudo", "-n", "systemctl", "restart", "shairport-sync"],
            capture_output=True, timeout=4,
        )
        time.sleep(0.3)  # brief settle so ALSA is fully released
        _set_airplay_active(False)
    except Exception:
        pass  # if it fails, MPD will surface the ALSA-busy error itself


async def cmd_handler(request):
    data   = await request.json()
    action = data.get("action", "")

    def do_mpd():
        c = MPDClient(); c.timeout = 3
        c.connect(MPD_HOST, MPD_PORT)
        try:
            if action == "play":
                _kick_airplay_for_mpd()
                c.play()
                _set_play_intent(True)
            elif action == "pause":
                c.pause()
                _set_play_intent(False)
            elif action == "toggle":
                s = c.status()
                if s.get("state") == "play":
                    c.pause()
                    _set_play_intent(False)
                else:
                    _kick_airplay_for_mpd()
                    c.play()
                    _set_play_intent(True)
            elif action == "next":
                c.next()
            elif action == "prev":
                c.previous()
            elif action == "volume":
                c.setvol(int(data.get("value", 50)))
            elif action == "seek":
                c.seekcur(int(data.get("value", 0)))
            elif action == "play_radio":
                _kick_airplay_for_mpd()
                c.clear()
                for url in data.get("urls", []):
                    c.add(url)
                c.play()
                _set_play_intent(True)
            elif action == "play_path":
                _kick_airplay_for_mpd()
                c.clear()
                c.add(data.get("path", ""))
                c.play()
                _set_play_intent(True)
            elif action == "play_station":
                station = data.get("station") or {}
                url = station.get("url", "")
                if url:
                    _kick_airplay_for_mpd()
                    c.clear()
                    c.add(url)
                    c.play()
                    _set_play_intent(True)
                    set_cover_for_station(station)
        finally:
            c.close()

    try:
        await asyncio.get_event_loop().run_in_executor(None, do_mpd)
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)


# ─── Reference test tones (local FLAC files in /var/lib/mpd/music/HiRes-Demo) ─
# Useful for verifying the audio path / L+R channel balance / hi-res capability.
# MPD paths are relative to music_directory.
REFERENCE_TRACKS = [
    {"name": "Sine Sweep 20 Hz – 20 kHz",
     "url": "HiRes-Demo/01-Sine-Sweep-20Hz-20kHz-24bit-96kHz.flac",
     "codec": "FLAC", "bitrate": 24*96, "tags": "test,reference,sweep",
     "description": "Frequency response check · 24-bit / 96 kHz"},
    {"name": "Pink Noise",
     "url": "HiRes-Demo/02-Pink-Noise-24bit-96kHz.flac",
     "codec": "FLAC", "bitrate": 24*96, "tags": "test,reference,noise",
     "description": "System balance / acoustic measurement · 24-bit / 96 kHz"},
    {"name": "Multitone 100 Hz + 1 kHz + 10 kHz",
     "url": "HiRes-Demo/03-Multitone-100Hz-1kHz-10kHz-24bit-96kHz.flac",
     "codec": "FLAC", "bitrate": 24*96, "tags": "test,reference,multitone",
     "description": "Intermodulation / multi-tone test · 24-bit / 96 kHz"},
    {"name": "1 kHz Reference Tone",
     "url": "HiRes-Demo/04-Reference-1kHz-24bit-192kHz.flac",
     "codec": "FLAC", "bitrate": 24*192, "tags": "test,reference,pure-tone",
     "description": "Pure 1 kHz reference · 24-bit / 192 kHz"},
    {"name": "L / R Channel Test",
     "url": "HiRes-Demo/05-LR-Channel-Test-24bit-96kHz.flac",
     "codec": "FLAC", "bitrate": 24*96, "tags": "test,reference,channel",
     "description": "Speaker / channel verification · 24-bit / 96 kHz"},
]


# ─── Station endpoints ───────────────────────────────────────────────────────
async def stations_featured(request):
    return web.json_response(FEATURED_STATIONS)


async def stations_reference(request):
    return web.json_response(REFERENCE_TRACKS)


async def stations_search(request):
    q = request.query.get("q", "").strip()
    if not q:
        return web.json_response([])
    raw = await rb_request("stations/search", {
        "name": q, "limit": "60", "order": "votes", "reverse": "true",
        "hidebroken": "true",
    })
    return web.json_response([normalize_station(s) for s in raw])


async def stations_by_tag(request):
    tag = request.match_info["tag"]
    raw = await rb_request(f"stations/bytagexact/{tag}", {
        "limit": "60", "order": "votes", "reverse": "true", "hidebroken": "true",
    })
    return web.json_response([normalize_station(s) for s in raw])


async def stations_by_country(request):
    country = request.match_info["country"]
    raw = await rb_request(f"stations/bycountry/{country}", {
        "limit": "60", "order": "votes", "reverse": "true", "hidebroken": "true",
    })
    return web.json_response([normalize_station(s) for s in raw])


async def stations_by_codec(request):
    codec = request.match_info["codec"]
    raw = await rb_request(f"stations/bycodecexact/{codec}", {
        "limit": "60", "order": "bitrate", "reverse": "true", "hidebroken": "true",
    })
    return web.json_response([normalize_station(s) for s in raw])


async def stations_popular(request):
    raw = await rb_request("stations/topvote/60", {"hidebroken": "true"})
    return web.json_response([normalize_station(s) for s in raw])


async def stations_genres(request):
    """Return a curated list of common genres for the menu."""
    return web.json_response([
        "jazz", "classical", "rock", "electronic", "ambient", "blues",
        "folk", "indie", "metal", "country", "reggae", "world",
        "hip-hop", "soul", "funk", "pop", "alternative", "baroque",
        "chillout", "downtempo", "house", "techno", "trance", "drum-and-bass",
    ])


async def stations_countries(request):
    return web.json_response([
        {"code": "United States",  "name": "United States"},
        {"code": "United Kingdom", "name": "United Kingdom"},
        {"code": "Germany",        "name": "Germany"},
        {"code": "France",         "name": "France"},
        {"code": "Italy",          "name": "Italy"},
        {"code": "Spain",          "name": "Spain"},
        {"code": "Netherlands",    "name": "Netherlands"},
        {"code": "Japan",          "name": "Japan"},
        {"code": "Australia",      "name": "Australia"},
        {"code": "Canada",         "name": "Canada"},
        {"code": "Brazil",         "name": "Brazil"},
        {"code": "Sweden",         "name": "Sweden"},
        {"code": "Norway",         "name": "Norway"},
        {"code": "Argentina",      "name": "Argentina"},
        {"code": "Mexico",         "name": "Mexico"},
    ])


# ─── Favorites endpoints ─────────────────────────────────────────────────────
async def favorites_list(request):
    with favorites_lock:
        return web.json_response(load_favorites())


async def favorites_add(request):
    station = await request.json()
    if not isinstance(station, dict) or not station.get("url"):
        return web.json_response({"ok": False, "error": "invalid station"}, status=400)
    with favorites_lock:
        favs = load_favorites()
        # Avoid duplicates by URL
        if not any(f.get("url") == station["url"] for f in favs):
            favs.append(station)
            save_favorites(favs)
    return web.json_response({"ok": True})


async def favorites_remove(request):
    station = await request.json()
    url = station.get("url", "")
    with favorites_lock:
        favs = load_favorites()
        favs = [f for f in favs if f.get("url") != url]
        save_favorites(favs)
    return web.json_response({"ok": True})


async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=15)
    await ws.prepare(request)
    clients.add(ws)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                break
    finally:
        clients.discard(ws)
    return ws


async def broadcast_loop(app):
    interval = 1.0 / BROADCAST_HZ
    state_counter = 0
    while True:
        await asyncio.sleep(interval)
        if not clients:
            continue
        with state.lock:
            payload = {
                "type":     "frame",
                "L_rms":    float(state.l_rms_db),
                "R_rms":    float(state.r_rms_db),
                "L_peak":   float(state.l_peak_db),
                "R_peak":   float(state.r_peak_db),
                "spectrum": [float(x) for x in state.spectrum],
            }
            state_counter += 1
            if state_counter >= BROADCAST_HZ // 2:
                payload["now"] = dict(state.now)
                with cover_state.lock:
                    payload["cover"] = {
                        "url":  cover_state.url,
                        "name": cover_state.name,
                    }
                state_counter = 0
        text = json.dumps(payload)
        dead = []
        for c in list(clients):
            try:
                await c.send_str(text)
            except Exception:
                dead.append(c)
        for c in dead:
            clients.discard(c)


async def on_startup(app):
    threading.Thread(target=fifo_reader, daemon=True).start()
    threading.Thread(target=mpd_poller,  daemon=True).start()
    app["bcast"] = asyncio.create_task(broadcast_loop(app))


async def on_shutdown(app):
    app["bcast"].cancel()
    for c in list(clients):
        await c.close()


import asyncio
import re
import subprocess
from pathlib import Path


# ─── helpers ────────────────────────────────────────────────────────────────
async def _run(cmd, timeout=10):
    """Run a shell command and return (returncode, stdout, stderr) as strings."""
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return proc.returncode, out.decode("utf-8", errors="replace"), err.decode("utf-8", errors="replace")
    except asyncio.TimeoutError:
        try: proc.kill()
        except: pass
        return -1, "", "timeout"


# ─── /api/network/status ────────────────────────────────────────────────────
async def network_status(request):
    """Current WiFi connection info."""
    rc, out, _ = await _run(["nmcli", "-t", "-f",
        "ACTIVE,SSID,SIGNAL,SECURITY,DEVICE", "device", "wifi", "list"])
    ssid = signal = security = ""
    if rc == 0:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 5 and parts[0] == "yes":
                ssid, signal, security = parts[1], parts[2], parts[3]
                break

    rc, ip_out, _ = await _run(["ip", "-4", "-br", "addr", "show", "wlan0"])
    ip = ""
    if rc == 0 and ip_out.strip():
        m = re.search(r"\s(\d+\.\d+\.\d+\.\d+)/", ip_out)
        ip = m.group(1) if m else ""

    rc, mac_out, _ = await _run(["cat", "/sys/class/net/wlan0/address"])
    mac = mac_out.strip() if rc == 0 else ""

    return web.json_response({
        "ssid": ssid,
        "signal": signal,
        "security": security,
        "ip": ip,
        "mac": mac,
        "interface": "wlan0",
    })


# ─── /api/network/forget-and-hotspot ────────────────────────────────────────
async def network_forget_hotspot(request):
    """Wipe WiFi credentials and reboot into Comitup hotspot mode."""
    async def do_wipe_and_reboot():
        await asyncio.sleep(2)  # let the response flush
        nm_dir = Path("/etc/NetworkManager/system-connections")
        # Wipe everything except Comitup's own hotspot profile
        for f in nm_dir.glob("*.nmconnection"):
            try: f.unlink()
            except: pass
        await _run(["sudo", "systemctl", "reboot"], timeout=5)

    asyncio.create_task(do_wipe_and_reboot())
    return web.json_response({"ok": True, "rebooting_in": 2})


# ─── /api/bt/devices ────────────────────────────────────────────────────────
async def bt_devices(request):
    """Return paired Bluetooth devices with their state."""
    rc, out, _ = await _run(["sudo", "bluetoothctl", "devices", "Paired"])
    if rc != 0:
        return web.json_response([])
    devices = []
    for line in out.splitlines():
        m = re.match(r"^Device\s+([0-9A-F:]{17})\s+(.+)$", line.strip(), re.I)
        if not m: continue
        mac, alias = m.group(1), m.group(2)
        # Get full info
        rc, info_out, _ = await _run(["sudo", "bluetoothctl", "info", mac])
        if rc != 0: continue
        name = ""
        connected = trusted = is_audio_sink = False
        for il in info_out.splitlines():
            il = il.strip()
            if il.startswith("Name:"):     name = il[5:].strip()
            elif il.startswith("Connected: yes"): connected = True
            elif il.startswith("Trusted: yes"):   trusted = True
            elif "Audio Sink" in il:              is_audio_sink = True
        devices.append({
            "mac": mac,
            "name": name or alias,
            "connected": connected,
            "trusted": trusted,
            "audio_sink": is_audio_sink,
        })
    return web.json_response(devices)


# ─── /api/bt/scan ───────────────────────────────────────────────────────────
async def bt_scan(request):
    """Scan for nearby Bluetooth devices (BR/EDR + LE) for ~25 seconds."""
    # Force BR/EDR transport for finding speakers
    proc = await asyncio.create_subprocess_exec(
        "sudo", "bluetoothctl",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        proc.stdin.write(b"menu scan\ntransport bredr\nback\nscan on\n")
        await proc.stdin.drain()
        await asyncio.sleep(22)
        proc.stdin.write(b"scan off\nquit\n")
        await proc.stdin.drain()
        await proc.wait()
    except Exception as e:
        try: proc.kill()
        except: pass

    # Now list discovered devices (excluding paired ones — those are in /api/bt/devices)
    rc, paired_out, _ = await _run(["sudo", "bluetoothctl", "devices", "Paired"])
    paired_macs = set()
    for line in paired_out.splitlines():
        m = re.match(r"^Device\s+([0-9A-F:]{17})", line.strip(), re.I)
        if m: paired_macs.add(m.group(1))

    rc, all_out, _ = await _run(["sudo", "bluetoothctl", "devices"])
    devices = []
    for line in all_out.splitlines():
        m = re.match(r"^Device\s+([0-9A-F:]{17})\s+(.+)$", line.strip(), re.I)
        if not m: continue
        mac, alias = m.group(1), m.group(2)
        if mac in paired_macs: continue
        # Only include devices with a real name (drop privacy-MAC BLE beacons)
        rc, info_out, _ = await _run(["sudo", "bluetoothctl", "info", mac])
        name = ""
        for il in info_out.splitlines():
            il = il.strip()
            if il.startswith("Name:"): name = il[5:].strip(); break
        if name and not re.match(r"^[0-9A-F\-]{17}$", name, re.I):
            devices.append({"mac": mac, "name": name})
    return web.json_response(devices)


# ─── /api/bt/pair ───────────────────────────────────────────────────────────
async def bt_pair(request):
    """Pair, trust, and connect a Bluetooth device by MAC."""
    data = await request.json()
    mac = data.get("mac", "")
    if not re.match(r"^[0-9A-F:]{17}$", mac, re.I):
        return web.json_response({"ok": False, "error": "invalid MAC"}, status=400)

    proc = await asyncio.create_subprocess_exec(
        "sudo", "bluetoothctl",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        cmds = (
            f"agent NoInputNoOutput\ndefault-agent\n"
            f"pair {mac}\n"
        ).encode()
        proc.stdin.write(cmds)
        await proc.stdin.drain()
        await asyncio.sleep(8)
        proc.stdin.write(f"trust {mac}\nconnect {mac}\nquit\n".encode())
        await proc.stdin.drain()
        out, _ = await proc.communicate()
        text = out.decode("utf-8", errors="replace")
        success = "Pairing successful" in text or "already paired" in text.lower()
        return web.json_response({"ok": success, "log": text[-2000:]})
    except Exception as e:
        try: proc.kill()
        except: pass
        return web.json_response({"ok": False, "error": str(e)}, status=500)


async def bt_forget(request):
    data = await request.json(); mac = data.get("mac", "")
    rc, _, err = await _run(["sudo", "bluetoothctl", "remove", mac])
    return web.json_response({"ok": rc == 0, "error": err})


async def bt_connect(request):
    data = await request.json(); mac = data.get("mac", "")
    rc, _, err = await _run(["sudo", "bluetoothctl", "connect", mac])
    return web.json_response({"ok": rc == 0, "error": err})


async def bt_disconnect(request):
    data = await request.json(); mac = data.get("mac", "")
    rc, _, err = await _run(["sudo", "bluetoothctl", "disconnect", mac])
    return web.json_response({"ok": rc == 0, "error": err})


# ─── /api/system/info ───────────────────────────────────────────────────────
async def system_info(request):
    info = {}

    # Uptime
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        d, secs = divmod(int(secs), 86400)
        h, secs = divmod(secs, 3600)
        m, _ = divmod(secs, 60)
        info["uptime"] = f"{d}d {h}h {m}m" if d else f"{h}h {m}m"
    except: info["uptime"] = "—"

    # CPU temp
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            info["cpu_temp_c"] = round(int(f.read().strip()) / 1000.0, 1)
    except: info["cpu_temp_c"] = None

    # Hostname + kernel
    rc, out, _ = await _run(["uname", "-rn"])
    if rc == 0:
        parts = out.strip().split()
        info["hostname"] = parts[0] if parts else ""
        info["kernel"]   = parts[1] if len(parts) > 1 else ""

    # IPs
    rc, out, _ = await _run(["ip", "-4", "-br", "addr"])
    info["interfaces"] = []
    if rc == 0:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] != "lo" and parts[1] == "UP":
                info["interfaces"].append({"name": parts[0], "ip": parts[2].split("/")[0]})

    # Memory
    try:
        with open("/proc/meminfo") as f:
            mem = dict(line.split(":") for line in f.read().splitlines() if ":" in line)
        info["mem_total_mb"] = int(mem.get("MemTotal", "0").strip().split()[0]) // 1024
        info["mem_avail_mb"] = int(mem.get("MemAvailable", "0").strip().split()[0]) // 1024
    except: pass

    # Service health
    services = ["mpd", "shairport-sync", "streamer-webapp", "nqptp", "bluetooth", "comitup"]
    info["services"] = {}
    for s in services:
        rc, out, _ = await _run(["systemctl", "is-active", s])
        info["services"][s] = out.strip()

    return web.json_response(info)


async def system_reboot(request):
    async def do_reboot():
        await asyncio.sleep(2)
        await _run(["sudo", "systemctl", "reboot"], timeout=5)
    asyncio.create_task(do_reboot())
    return web.json_response({"ok": True, "rebooting_in": 2})


async def system_shutdown(request):
    async def do_shutdown():
        await asyncio.sleep(2)
        await _run(["sudo", "systemctl", "poweroff"], timeout=5)
    asyncio.create_task(do_shutdown())
    return web.json_response({"ok": True, "shutting_down_in": 2})


async def internal_airplay(request):
    """Called by shairport-sync hooks (see /etc/shairport-sync.conf).
    POST body: state=start|stop. Tracks AirPlay session so MPD auto-resume
    doesn't fight an active AirPlay client."""
    try:
        data = await request.post()
        state_val = (data.get("state") or "").lower()
    except Exception:
        state_val = ""
    if state_val == "start":
        _set_airplay_active(True)
    elif state_val == "stop":
        _set_airplay_active(False)
    return web.json_response({"ok": True, "state": state_val})


async def network_scan(request):
    """Return list of nearby WiFi networks visible to wlan0."""
    rc, out, _ = await _run([
        "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,IN-USE",
        "device", "wifi", "list", "ifname", "wlan0", "--rescan", "yes"
    ], timeout=15)
    if rc != 0:
        return web.json_response([])

    seen = {}
    for line in out.splitlines():
        # nmcli -t separates by ":" but allows escaped ":" inside fields with "\:"
        # Simple split is fine for our 4-field schema since SSID is first and last meaningful
        parts = line.split(":")
        if len(parts) < 4:
            continue
        ssid = parts[0].replace("\\:", ":")
        signal = parts[1] if parts[1].isdigit() else "0"
        security = parts[2] or "open"
        in_use = parts[3] == "*"
        if not ssid or ssid == "--":
            continue
        # Keep highest-signal entry per SSID
        if ssid not in seen or int(signal) > int(seen[ssid]["signal"]):
            seen[ssid] = {
                "ssid": ssid,
                "signal": signal,
                "security": security,
                "in_use": in_use,
            }
    nets = sorted(seen.values(), key=lambda x: -int(x["signal"]))
    return web.json_response(nets)


async def network_connect(request):
    """Connect to a WiFi network by SSID + password.
    Runs in a delayed task so the response can flush before NM reconfigures.
    """
    data = await request.json()
    ssid = data.get("ssid", "").strip()
    password = data.get("password", "")
    if not ssid:
        return web.json_response({"ok": False, "error": "SSID required"}, status=400)

    async def do_connect():
        await asyncio.sleep(1.0)  # let response flush + browser reconnect
        cmd = ["nmcli", "device", "wifi", "connect", ssid, "ifname", "wlan0"]
        if password:
            cmd += ["password", password]
        rc, out, err = await _run(cmd, timeout=45)
        # Result is logged but not returned (the requesting client may have
        # disconnected if we switched away from its network).
        print(f"[net-connect] ssid={ssid} rc={rc} out={out.strip()[:200]} err={err.strip()[:200]}",
              flush=True)

    asyncio.create_task(do_connect())
    return web.json_response({
        "ok": True,
        "ssid": ssid,
        "note": "Connection attempt started. The streamer may briefly drop off the network "
                "while it switches. If it doesn't reappear within 60 seconds, the password "
                "may be wrong — connect to the setup hotspot to recover."
    })


USER_STATIONS_FILE = Path("/var/lib/streamer/user_stations.json")
user_stations_lock = threading.Lock()


def _load_user_stations():
    """Load user station customizations. Returns dict with 'added' + 'hidden' keys."""
    try:
        with open(USER_STATIONS_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {}
        data.setdefault("added", [])
        data.setdefault("hidden", [])
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"added": [], "hidden": []}


def _save_user_stations(data):
    USER_STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = USER_STATIONS_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    tmp.replace(USER_STATIONS_FILE)


def _merge_featured():
    """Compose effective featured list: defaults minus hidden plus user-added."""
    with user_stations_lock:
        u = _load_user_stations()
    hidden = set(u.get("hidden", []))
    out = []
    for s in FEATURED_STATIONS:
        if s.get("name") not in hidden:
            x = dict(s)
            x["origin"] = "default"
            out.append(x)
    for a in u.get("added", []):
        x = dict(a)
        x["origin"] = "custom"
        out.append(x)
    return out


# Override the original /api/stations/featured to use the merged list
async def stations_featured(request):
    return web.json_response(_merge_featured())


async def stations_add_custom(request):
    """POST {name, url, codec?, bitrate?, tags?, country?, description?}."""
    data = await request.json()
    name = (data.get("name") or "").strip()
    url  = (data.get("url")  or "").strip()
    if not name or not url:
        return web.json_response({"ok": False, "error": "name and url required"}, status=400)
    if not (url.startswith("http://") or url.startswith("https://")):
        return web.json_response({"ok": False, "error": "url must start with http:// or https://"}, status=400)

    station = {
        "name":        name,
        "url":         url,
        "homepage":    data.get("homepage", ""),
        "favicon":     data.get("favicon", ""),
        "codec":       (data.get("codec") or "").upper(),
        "bitrate":     int(data.get("bitrate", 0) or 0),
        "tags":        data.get("tags", "custom"),
        "country":     data.get("country", ""),
        "language":    data.get("language", ""),
        "description": data.get("description", "Custom station"),
    }

    with user_stations_lock:
        u = _load_user_stations()
        # Avoid duplicates by URL
        u["added"] = [a for a in u["added"] if a.get("url") != url]
        u["added"].append(station)
        _save_user_stations(u)
    return web.json_response({"ok": True, "station": station})


async def stations_hide(request):
    """POST {name} — hide a Featured station from view."""
    data = await request.json()
    name = (data.get("name") or "").strip()
    if not name:
        return web.json_response({"ok": False, "error": "name required"}, status=400)
    with user_stations_lock:
        u = _load_user_stations()
        if name not in u["hidden"]:
            u["hidden"].append(name)
            _save_user_stations(u)
    return web.json_response({"ok": True})


async def stations_unhide(request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    with user_stations_lock:
        u = _load_user_stations()
        u["hidden"] = [n for n in u["hidden"] if n != name]
        _save_user_stations(u)
    return web.json_response({"ok": True})


async def stations_remove_custom(request):
    """POST {url} — remove a user-added station by URL."""
    data = await request.json()
    url = (data.get("url") or "").strip()
    with user_stations_lock:
        u = _load_user_stations()
        u["added"] = [a for a in u["added"] if a.get("url") != url]
        _save_user_stations(u)
    return web.json_response({"ok": True})


async def stations_reset(request):
    """Wipe all station customizations — restores the default Featured list."""
    with user_stations_lock:
        try: USER_STATIONS_FILE.unlink()
        except FileNotFoundError: pass
    return web.json_response({"ok": True})


async def stations_user_state(request):
    """Return the current user customizations (for diagnostics / Settings UI)."""
    with user_stations_lock:
        return web.json_response(_load_user_stations())


def main():
    app = web.Application()
    app.router.add_get("/",                       index)
    app.router.add_get("/ws",                     ws_handler)
    app.router.add_get("/api/brand",              brand_handler)
    app.router.add_get("/api/themes",             themes_list)
    app.router.add_post("/api/themes/set",        theme_set)
    app.router.add_post("/api/cmd",               cmd_handler)
    # Stations
    app.router.add_get("/api/stations/featured",  stations_featured)
    app.router.add_get("/api/stations/reference", stations_reference)
    app.router.add_get("/api/stations/user_state",     stations_user_state)
    app.router.add_post("/api/stations/add_custom",    stations_add_custom)
    app.router.add_post("/api/stations/hide",          stations_hide)
    app.router.add_post("/api/stations/unhide",        stations_unhide)
    app.router.add_post("/api/stations/remove_custom", stations_remove_custom)
    app.router.add_post("/api/stations/reset",         stations_reset)

    app.router.add_get("/api/stations/search",    stations_search)
    app.router.add_get("/api/stations/popular",   stations_popular)
    app.router.add_get("/api/stations/genres",    stations_genres)
    app.router.add_get("/api/stations/countries", stations_countries)
    app.router.add_get("/api/stations/by_tag/{tag}",         stations_by_tag)
    app.router.add_get("/api/stations/by_country/{country}", stations_by_country)
    app.router.add_get("/api/stations/by_codec/{codec}",     stations_by_codec)
    # Favorites
    app.router.add_get("/api/favorites",          favorites_list)
    app.router.add_post("/api/favorites/add",     favorites_add)
    app.router.add_post("/api/favorites/remove",  favorites_remove)
    # Static (catch-all, must be last)
    # Settings — Network
    app.router.add_get("/api/network/status",            network_status)
    app.router.add_get("/api/network/scan",     network_scan)
    app.router.add_post("/api/network/connect", network_connect)
    app.router.add_post("/api/network/forget-and-hotspot", network_forget_hotspot)
    # Settings — Bluetooth
    app.router.add_get("/api/bt/devices",                bt_devices)
    app.router.add_post("/api/bt/scan",                  bt_scan)
    app.router.add_post("/api/bt/pair",                  bt_pair)
    app.router.add_post("/api/bt/forget",                bt_forget)
    app.router.add_post("/api/bt/connect",               bt_connect)
    app.router.add_post("/api/bt/disconnect",            bt_disconnect)
    # Settings — System
    app.router.add_get("/api/system/info",               system_info)
    app.router.add_post("/api/system/reboot",            system_reboot)
    app.router.add_post("/api/system/shutdown",          system_shutdown)
    app.router.add_post("/api/internal/airplay",         internal_airplay)
    app.router.add_get("/{name:.+}",              static_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=HTTP_PORT, access_log=None)


if __name__ == "__main__":
    main()
