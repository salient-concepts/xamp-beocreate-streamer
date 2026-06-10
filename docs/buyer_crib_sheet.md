# xAMP Beocreate Audiophile Streamer
## Quick Start Guide

Thank you for your purchase. This unit ships with **xAMP Audio Streamer**,
a custom hi-fi streaming OS built specifically for the **HiFiBerry Beocreate**
4-channel amplifier + DSP HAT. Everything below works out of the box.

---

## 1 · First Power-On

1. Wire your **speakers** directly to the rear amp output terminals. Two
   pairs are available:
   - **High-power pair (2 × 60 W)** — woofer / full-range channels
   - **Lower-power pair (2 × 30 W)** — tweeter channels
   For a standard 2-speaker setup, use either pair. The unit ships with
   IIR filter slots cleared so any pair emits full-range stereo.
2. Connect **Ethernet** to the rear RJ-45 port. *Wired ethernet is strongly
   recommended for AirPlay 2 stability and bit-perfect FLAC streaming.* If
   you prefer Wi-Fi, the Pi 4 supports both **2.4 GHz and 5 GHz**.
3. Plug in the **power cord**, press the **front-panel power button**. The
   unit boots in about 60 seconds. The Pi LED on the back blinks during
   boot and goes steady when ready.

---

## 2 · Reach the Web UI from Your Phone or Laptop

The unit advertises itself on your network via mDNS / Bonjour. From any
browser on the same network, open:

> **http://xamp-beocreate.local:8081**

If your network or device doesn't support `.local` lookup, find the unit's
IP address in your router's DHCP client list (look for hostname
`xamp-beocreate`), then open:

> **http://[that-ip]:8081**

Example: `http://192.168.1.45:8081`

You'll see the xAMP control surface — four tabs at the top:

- **PLAYER** — now-playing card, VU meters, spectrum analyzer, transport, volume
- **STATIONS** — browse 50,000+ internet radio stations, search, favourites
- **SETTINGS** — themes, Wi-Fi, system, **Power Management** (graceful Reboot + Shut Down)
- **ABOUT** — hardware specs, alternative software guide

Add the page to your phone's home screen for an app-like icon.

---

## 3 · Play Music

**Three ways to start playback:**

### A. Internet Radio (50,000+ stations)
1. Tap the **STATIONS** tab
2. Browse Featured / By Genre / By Country / Hi-Res / Popular / Favourites,
   or use the search bar
3. Tap any station tile → playback starts immediately
4. Tap the **★** to favourite a station

### B. AirPlay 2 (from iPhone, iPad, Mac)
1. Open **Apple Music**, **Spotify**, or any audio app
2. Start playing a song
3. Tap the AirPlay icon → select **xAMP Beocreate** from the device list
4. Volume slider on your phone now controls the streamer
5. If you start a station in the web UI, AirPlay yields the DAC cleanly.
   Whichever you ask for last, wins.

### C. Hi-Res FLAC Reference Tones (preloaded)
- Five 24-bit reference tracks live in the local library under
  *STATIONS → Library*:
  - 24-bit / 96 kHz log sine sweep (20 Hz – 20 kHz)
  - 24-bit / 96 kHz pink noise
  - 24-bit / 96 kHz multitone (100 Hz + 1 kHz + 10 kHz)
  - 24-bit / 192 kHz pure 1 kHz reference
  - 24-bit / 96 kHz L/R channel test

---

## 4 · DSP Tuning (Optional but Powerful)

The Beocreate HAT carries an **Analog Devices ADAU1452 SigmaStudio DSP**
that's network-configurable. The unit runs `sigmatcpserver` on port 8086
so you can tune from any device on your network:

- **HiFiBerry's BeoCreate2 web app** — install on any laptop or another Pi;
  it'll auto-discover this streamer and give you a graphical interface for
  parametric EQ, crossovers, time alignment, and speaker presets. Designed
  for Bang & Olufsen 4000/6000-series, MS150, and any active-speaker
  conversion.
- **Analog Devices' SigmaStudio** (Windows) — full DSP design environment.
  Connect over the network at `xamp-beocreate.local:8086`.

The 4-way default profile is burned to the Beocreate's EEPROM and
auto-loads on every boot. Your customizations override from a known-clean
baseline — IIR filter slots are auto-cleared each boot. A 2-pass verified
DSP initializer ensures clean cold-boot state.

---

## 5 · Themes (Settings tab)

Five colour palettes are pre-installed. Tap any swatch to apply instantly.

| Theme | Style |
|---|---|
| **Synthwave** (default) | Neon magenta + cyan, dark purple |
| **Vintage Hi-Fi** | Cream + brass, warm dark — classic Marantz vibe |
| **McIntosh Blue** | Cream face + electric blue, the Mac aesthetic |
| **Aurora** | Emerald + violet, northern lights |
| **Tron** | Pure black + electric blue + white, minimal |

---

## 6 · Shutting Down Properly

The front-panel button is a **power switch** — it cuts the ATX rail
directly. To shut down cleanly:

1. Open the web UI → **SETTINGS** tab
2. Tap the red **Shut Down** circle under *Power Management*
3. Wait ~10 seconds for the Pi LED on the back to go dark
4. Then press the front-panel switch to cut power

The OS uses ext4 journaling, so an occasional hard cut won't corrupt the
SD card — but the soft shutdown is gentler.

---

## 7 · System Access (advanced)

The unit runs **Raspberry Pi OS Trixie** with these services:

- **MPD** (Music Player Daemon) on port 6600 — forced to 48 kHz output to
  match the DSP's native core rate
- **xAMP web UI** on port 8081 (this control surface)
- **shairport-sync** (v5.0.2 source-built) + nqptp for AirPlay 2
- **sigmatcpserver** on port 8086 for DSP control
- **dsp-clear-filters** — runs `xamp-dsp-init` at boot to clean-initialize the DSP

**SSH credentials:**
- Host: `pi@xamp-beocreate.local`
- User: `pi`
- Password: `raspberry`
- *(Change with `passwd` after first login.)*

**Key files:**
- `/opt/streamer-webapp/` — xAMP web app source
- `/usr/local/sbin/xamp-dsp-init` — 2-pass DSP cold-boot initializer
- `/usr/local/sbin/xamp-airplay-event` — shairport-sync hook script
- `/etc/streamer/brand.conf` — UI branding (editable JSON)
- `/etc/streamer/theme.conf` — active theme
- `/var/lib/streamer/favorites.json` — saved stations
- `/var/lib/hifiberry/dspprogram.xml` — active DSP profile
- `/var/lib/mpd/music/HiRes-Demo/` — preloaded reference tracks

---

## 8 · Alternative Software (you're not locked in)

The hardware is open — any Pi-based audio OS that recognizes the HiFiBerry
Beocreate HAT will run on it:

| Stack | Price | Best for |
|---|---|---|
| **xAMP** (preinstalled) | Free | Out-of-the-box use, custom UI, AirPlay 2, B&O conversion tuning |
| **Volumio** | Free / €30 | Most popular Pi audiophile OS |
| **Moode Audio** | Free | Pure audiophile, deep DSP, Camilla DSP integrated |
| **piCorePlayer + LMS** | Free | Squeezebox / Lyrion ecosystem |
| **RoPieee + Roon** | $130/yr | Roon Ready endpoint |
| **HQPlayer NAA** | €230 | Audiophile upsampling holy grail |

To switch: pull the SD card, flash a different OS image with Raspberry Pi
Imager, reinsert. Most OSes auto-detect the Beocreate HAT.

> ⚠ Switching the SD card image **wipes xAMP, favourites, and any DSP
> tuning you've stored**. If you want to come back later, keep the
> original SD image.

---

## 9 · Specifications

| | |
|---|---|
| **Compute** | Raspberry Pi 4 Model B (4 GB RAM, aarch64, Pi OS Trixie) |
| **DSP** | Analog Devices ADAU1452 (SigmaStudio) |
| **DAC** | PCM5122 (24-bit / 192 kHz) |
| **Amplifier** | Dual TAS5754M class-D — 2 × 30 W + 2 × 60 W |
| **Inputs** | I2S from Pi, S/PDIF (optional via DSP routing) |
| **Outputs** | 4 × speaker channels (Phoenix-style terminals) |
| **PSU** | SilverStone SX600-G 600 W SFX (80 Plus Gold, modular) |
| **Power management** | Pod Bay 3 Mini ATX PSU II adapter + BCM2711 hardware watchdog |
| **Network** | Gigabit Ethernet + dual-band 802.11ac (2.4 + 5 GHz) |
| **Chassis** | GOOHEE A99 mini-ITX (acrylic + wood, factory-engraved xAMP) — 8.87 × 9.92 × 8.05 in |

---

## 10 · Troubleshooting

**No sound from speakers?**
- Check speaker wires are seated in the rear terminals.
- Verify MPD volume on the web UI is above 0%.
- Open the web UI → PLAYER tab → confirm a track is playing.
- If using AirPlay, confirm phone and streamer are on the same Wi-Fi.

**Audio sounds noisy after a cold power-up?**
- The `xamp-dsp-init` service does a 2-pass DSP cold-boot initializer that
  resolves the documented cold-boot race. If you ever hear noise after a
  cold boot, give the unit 90 seconds to fully boot before pressing play.
- If the noise persists after a clean boot, re-run the initializer:
  `sudo systemctl restart dsp-clear-filters`

**Can't reach the web UI?**
- Try `http://xamp-beocreate.local:8081` from a device that supports mDNS.
- Confirm your phone/laptop is on the same Wi-Fi network.
- Check the unit's IP in your router's DHCP client list.

**Need to factory reset?**
- Stop xAMP services and re-flash the original SD card image (kept by
  seller — message via eBay).

---

## Support

This unit is sold as-is. The xAMP software is custom; the underlying
hardware (HiFiBerry Beocreate HAT) is documented at hifiberry.com.

For xAMP software issues: contact the seller via your eBay message thread.

---

*xAMP Audio Streamer · running on the HiFiBerry Beocreate platform · Salient Concepts*
