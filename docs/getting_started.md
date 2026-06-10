# xAMP Audio Streamer

## Quick Start Guide

*running on the **Beocreate** platform — HiFiBerry 4-channel amplifier HAT + Raspberry Pi 4*

---

> **Note:** xAMP is custom software built specifically for this unit. Keep it as long as you like, or switch to one of the alternatives (Volumio, Moode, Roon, LMS, HQPlayer, piCorePlayer) — see the **ABOUT** tab. The hardware is open: it'll run any Pi-based audio OS that recognizes the HiFiBerry Beocreate HAT.

### 1 — Connect

- **Speakers** wire directly to the unit's rear amplifier outputs. Two pairs of speaker terminals: the high-power pair (2 × 60 W) for woofers/full-range, the lower-power pair (2 × 30 W) for tweeters. For a regular 2-speaker setup, use either pair — the unit ships with the IIR crossover filters cleared so any pair gives full-range stereo.
- **Ethernet** to the rear RJ-45 port — *recommended* for AirPlay 2 stability and bit-perfect FLAC. Or use Wi-Fi (next step) — Pi 4 supports both **2.4 GHz and 5 GHz**.
- **Power cord** — the unit boots in about 60 seconds. Press the **front-panel power button** to power on. The Pi LED on the back blinks during boot and goes steady when ready.

### 2 — Wi-Fi setup (skip if you're using Ethernet)

If the unit isn't already on your network, it broadcasts its own setup hotspot for ~60 seconds after first boot.

1. On your phone, enable **airplane mode**, then turn **Wi-Fi back on** (this works around an iOS/Android setup-WiFi quirk)
2. Join the network: `xAMP-Beocreate-NNN` (no password)
3. The captive portal opens automatically — if not, open `http://10.41.0.1` in any browser
4. **Pick your home Wi-Fi** — either 2.4 GHz or 5 GHz, your choice. The Pi 4 handles both.
5. Enter your Wi-Fi password and submit. Your phone reconnects to your home Wi-Fi automatically.
6. The unit reboots once (~60 seconds) and joins your network.

### 3 — Reach the web UI

The unit advertises itself on your network via **mDNS / Bonjour** as `xAMP Beocreate`. From any phone, tablet, or computer on the same network, open:

**`http://xamp-beocreate.local:8081`**

If your network or device doesn't support `.local` lookup, log into your router and find the IP address it assigned to the unit (look for hostname `xamp-beocreate`), then open:

**`http://[that-ip]:8081`**

### 4 — Using the web UI

Four tabs at the top:

| | |
|---|---|
| **PLAYER** | Now-playing card, twin McIntosh-blue VU meters, 32-band spectrum analyzer, transport controls, volume slider |
| **STATIONS** | 50,000+ internet radio — sub-tabs for Featured (curated audiophile), Genre, Country, Hi-Res, Popular, Favorites. Tap a station to play. Tap **★** to save a favorite. |
| **SETTINGS** | Theme picker (5 looks), Wi-Fi switcher, system health, **Power Management** (graceful Reboot and Shut Down buttons) |
| **ABOUT** | Hardware specs, software credits, alternative-OS guide |

**AirPlay 2** — your iPhone, iPad, or Mac sees the unit as **xAMP Beocreate** in any AirPlay picker. You can switch between the radio app and AirPlay freely — whichever you ask for last, wins.

**Hi-res demo tones** are preloaded in the local library (24-bit / 96 kHz and 192 kHz reference tracks) under the *Stations → Library* sub-tab.

### 5 — Shutting down properly

The front-panel button is a power switch — it cuts the ATX rail directly. To shut down cleanly:

1. Open the web UI → **SETTINGS** tab
2. Tap the red **Shut Down** circle under *Power Management*
3. Wait ~10 seconds for the Pi LED on the back to go dark
4. Then press the front-panel switch to cut power

(Yanking power while the Pi is running won't kill the SD card immediately — the OS uses journaling — but the soft-shutdown is gentler.)

### 6 — Advanced

- **SSH:** `pi@xamp-beocreate.local` &nbsp; password `raspberry` *(change with `passwd` after first login)*
- **DSP tuning:** the Beocreate's ADAU1452 DSP is configurable over the network. Install the HiFiBerry **BeoCreate2** web app on any device on your network — it'll auto-discover this streamer at `xamp-beocreate.local:8086` and let you adjust crossovers, parametric EQ, time alignment, and speaker presets. Or use Analog Devices' SigmaStudio (Windows) for full DSP design.
- **Factory reset:** re-flash the original SD card image (kept by seller — message via eBay)
- **Switch OS:** see the *Alternative Software* card in the ABOUT tab. Most Pi-based audiophile OSes auto-detect the HiFiBerry Beocreate HAT.

---

**xAMP Audio Streamer** · Salient Concepts · sold as-is · questions via eBay message
