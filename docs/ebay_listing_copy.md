# eBay Listing — xAMP Beocreate Audiophile Streamer

*(paste into eBay's description editor — works in plain text or HTML mode)*

> **Status: DRAFT — placeholders marked `<TBD>` need filling before publishing.**

---

## TITLE (≤80 chars)

> **xAMP Audiophile Streamer · HiFiBerry Beocreate DSP · Pi 4 · AirPlay 2 · 600W ATX**

*(alt: `Custom Audiophile Streamer · Beocreate 4ch DSP DAC · Pi 4 · ATX PSU · AirPlay 2`)*

---

## SUMMARY BULLETS (eBay structured "item specifics")

- **Custom-built audiophile streamer** — hand-assembled by Salient Concepts in a **one-of-one custom mini-ITX chassis** (GOOHEE Acrytix A99 base, acrylic + wood, bespoke laser engraving)
- **HiFiBerry Beocreate 4-channel DSP + amplifier** — ADAU1452 SigmaStudio DSP, PCM5122 DAC stage, dual TAS5754M class-D, 2×30W + 2×60W
- **Raspberry Pi 4 Model B 4GB**, dual-band Wi-Fi (2.4 / 5 GHz)
- **SilverStone SX600-G** (600 W SFX, 80 Plus Gold, modular) feeding a **Pod Bay 3 Mini ATX PSU II** adapter — clean regulated 5 VDC back-power, front-panel power switch, **kernel hardware watchdog auto-reset** if Pi ever hangs
- **xAMP custom OS preinstalled** — see below
- **AirPlay 2 receiver** — built from source (shairport-sync 5.0.2 + nqptp PTP timing)
- **50,000+ internet radio stations** built-in
- **Bang & Olufsen Beocreate conversion-ready** — designed to drive 2- / 3- / 4-way passive speakers with programmable crossover, EQ, and time-alignment
- **Sold as-is, fully tested, working perfectly**

---

## FULL DESCRIPTION

### What you're buying

A **hand-built audiophile network streamer** from Salient Concepts, designed
specifically for owners of **Bang & Olufsen Beocreate active-speaker
conversions** — or anyone who wants a Pi-based streamer with serious power,
serious DSP, and a serious chassis.

This is not a stock HiFiBerry kit in a Pi case. The unit is built into a
**custom mini-ITX chassis** powered by a **600W SFF ATX power supply** for
clean, regulated, dedicated audio-grade power. The Pi is back-powered through
a **Pod Bay 3 Mini ATX PSU II adapter board** (designed and sold by
[Tom Tibbetts on Tindie](https://www.tindie.com/products/tomtibbetts/mini-atx-psu-desktop-atx-power-for-raspberry-pi/))
which gives the unit **proper desktop-grade power management**: single power
button does on / off / reboot / hard-kill, plus a hardware watchdog and
auto-reboot on power restoration. No SD-card corruption from yanked power.
No noisy USB wall-wart. Cleaner than typical Pi audio builds by design.

### Hardware

| | |
|---|---|
| **Compute** | Raspberry Pi 4 Model B Rev 1.4, **4 GB RAM**, aarch64, Pi OS Trixie |
| **DSP HAT** | HiFiBerry Beocreate 4-Channel Amplifier — ADAU1452 SigmaStudio DSP |
| **DAC stage** | PCM5122 24-bit, 192 kHz |
| **Amplifier** | Dual TAS5754M class-D — **2×30W + 2×60W** |
| **Power supply** | **SilverStone SX600-G** — 600 W, SFX form factor, **80 Plus Gold**, fully modular |
| **Power management** | Pod Bay 3 Mini ATX PSU II adapter (early revision, from [Tindie](https://www.tindie.com/products/tomtibbetts/mini-atx-psu-desktop-atx-power-for-raspberry-pi/)) — provides regulated 5 VDC + front-panel power switch |
| **Watchdog** | BCM2711 hardware watchdog, 60 s timeout, pinged by systemd-PID1 — auto-resets a hung kernel |
| **Networking** | Gigabit Ethernet + dual-band 802.11ac (2.4 GHz **+** 5 GHz) |
| **Storage** | 64 GB microSD with xAMP OS preflashed |
| **Chassis** | **GOOHEE A99** mini-ITX (acrylic + wood, dual-chamber, transparent + wood finish, ~3.2 lb empty) — **custom-cut panels + 0.3 mm precision laser engraving** by the manufacturer to Salient Concepts spec |
| **Chassis dimensions** | **8.87" W × 9.92" H × 8.05" D** (225 × 252 × 204 mm, height includes 0.71" / 18 mm case feet) |
| **Chassis status** | **Currently unavailable on Amazon** — base SKU no longer in stock at the manufacturer |

**Power architecture matters.** Most Pi-based audio builds run on USB-C
wall-warts that introduce switching noise into the analog stage. This unit
runs the Pi from a **dedicated regulated 5 VDC line off a 600 W
SilverStone SX600-G (80 Plus Gold) SFX supply**, fed through the Pod Bay 3
Mini ATX PSU II adapter board — same physical layout as a desktop PC, not
a phone-charger brick.

How it actually works:

- **Front-panel power switch** toggles the ATX rail. Press once to bring
  the Pi up; for shutdown, either trigger a graceful `sudo poweroff` from
  the web UI / SSH first or press the switch to drop the rail. The Pi
  runs ext4 with journaling, so the SD card is durable against the
  occasional hard cut.
- **Hardware watchdog** — systemd-PID1 pings the BCM2711's hardware
  watchdog device every few seconds. If the kernel ever hangs, the SoC
  hard-resets the Pi after 60 seconds and the PSU brings it back
  automatically. No babysitting.
- **Clean audio-grade 5 V rail** — desktop-class regulation, no USB-C
  wall-wart switching noise leaking into the analog stage.

### Chassis — a one-off, factory-engraved xAMP enclosure

The unit is built into a **GOOHEE A99 mini-ITX case** — a dual-chamber
acrylic-and-wood enclosure (clear acrylic panels on three sides, solid
wooden front, hidden cable chamber behind the wood). Cool to look at,
audiophile-appropriate, no plastic.

What makes **this specific case** unique:

- **The manufacturer customized the panels to Salient Concepts' spec.**
  Stock USB and GPU cutouts removed from the front. Acrylic front returned
  to clean uninterrupted clear. Acrylic back's I/O opening cut down from
  the stock 159 mm wide × full-height shield slot to a centered **79.5 mm**
  opening sized for the Pi's Ethernet + USB cluster. Side panels keep the
  bottom airflow vents, lose the fan cutouts.
- **Factory laser engraving** — wooden front, acrylic back, and both
  acrylic side panels are engraved with the **xAMP** wordmark in Allegro
  font flanked by musical notes, plus the tagline **"SMOOTH SOUNDS"** —
  done at **0.3 mm precision** by the case maker, not aftermarket.
  This is not a sticker. It's burned in. The case ships *as* an xAMP
  unit.
- **The base case is no longer available.** GOOHEE's A99 SKU shows as
  *"currently unavailable"* on Amazon — the manufacturer is not
  replenishing stock. The engraved/customized variant is not a SKU at
  all; it was a one-time run.

The net: even before you look at what's inside, you're getting a chassis
that exists in single-digit quantities worldwide, factory-engraved with
the xAMP brand, with bespoke panel cutouts you can't order again.

### Software — xAMP Audio Streamer

**A complete custom hi-fi streaming OS** built specifically for the Beocreate
hardware. Everything works out of the box:

**1 · Phone-friendly web control app (port 8081)**
- Open the streamer's IP from any phone / laptop browser
- Three tabs: **Player** · **Stations** · **About**
- Twin McIntosh-blue VU meters (cream face, blue needles, peak-hold)
- 32-band gold spectrum analyzer
- Transport controls + volume slider
- Add to home screen for an app-style icon

**2 · 50,000+ internet radio stations**
- Built-in browser via radio-browser.info — Featured / By Genre / By Country / Hi-Res / Most Popular / Search
- **Curated audiophile featured list** — Radio Paradise FLAC × 4, Linn Jazz, Linn Classical, Linn Radio, Naim Radio FLAC, BBC Radio 3, BBC 6 Music, France Musique, FIP, SomaFM × 5, Jazz24, WBGO, ABC Jazz, KEXP, WFMU, Klassik Radio Pure, Venice Classic Radio Italia
- **Favourites star button** — saved across reboots

**3 · AirPlay 2 receiver — built from source**
- Built from mikebrady's shairport-sync 5.0.2 + nqptp PTP companion daemon
- Shows up as a first-class AirPlay 2 device on iPhone, iPad, and Mac (`vv=2`, not the buried "Other Speakers" AirPlay 1 fallback)
- **Seamless bidirectional switching** between MPD radio and AirPlay — start a station in the web app and AirPlay disconnects cleanly; start AirPlay from your phone and MPD yields the DAC. Whichever you ask for, wins.

**4 · DSP integration — sigmatcpserver running on port 8086**
- HiFiBerry's BeoCreate2 web app or Analog Devices' SigmaStudio (Windows) can connect over the network to **configure crossovers, parametric EQ, time-alignment, and speaker presets** for B&O 4000/6000 series, MS150, or any active-speaker conversion
- Default profile (`4way-default.xml`) is burned to the Beocreate's EEPROM and auto-loaded at every boot via SELFBOOT
- IIR filter slots are auto-cleared on each boot to flat passthrough — your customizations override from a known-clean baseline

**5 · Audiophile signal path**
- MPD with **exclusive ALSA out** to `hw:sndrpihifiberry,0`
- No software resampling — bit-perfect from source to DSP to DAC to amps
- Performance CPU governor, MPD pinned to dedicated core, real-time scheduling
- HDMI audio disabled, USB audio class blacklisted, Wi-Fi power-save off — every dropout source eliminated

**6 · Comitup Wi-Fi onboarding**
- No headless config needed — first power-on broadcasts `xAMP-Beocreate-NNN` Wi-Fi
- Connect your phone, the captive portal opens automatically
- Pick your home Wi-Fi, enter password, done — the unit joins your network
- Supports **both 2.4 GHz and 5 GHz** (Pi 4 is dual-band, unlike Pi 3)

**7 · Five colour themes**
- **Synthwave** (default) · **Vintage Hi-Fi** · **McIntosh Blue** · **Aurora** · **Tron**

### What makes this listing different

- **You're not getting a Pi in a plastic case.** You're getting a custom audiophile rig with a real PSU, a real power management board, a factory-engraved xAMP-branded acrylic + wood chassis, and a real DSP-driven 4-channel amplifier.
- **The chassis is a one-off.** Manufacturer-engraved xAMP wordmark, custom panel cutouts to Salient Concepts spec, base SKU now unavailable — you can't replicate this case from the Amazon catalog.
- **Software is genuinely custom.** Not Volumio with a re-skin. Not stock HiFiBerry OS. A purpose-built MPD + aiohttp + shairport-sync stack with bidirectional preemption logic and DSP integration.
- **B&O conversion-ready.** This isn't sold as a finished consumer speaker. It's sold as the *engine* for an audiophile B&O conversion project — drop it into any Beocreate-compatible amp slot and tune to your speakers via BeoCreate2.

### What's in the box

- 1 × xAMP Beocreate audiophile streamer (custom mini-ITX build)
- 1 × IEC C13 power cable for the SX600-G
- 1 × Printed quick-start guide
- 1 × SD card preflashed with xAMP OS

### Not locked in — switch to anything

The unit is a Raspberry Pi 4 + HiFiBerry Beocreate HAT. Any Pi-based audio
OS will run on it:

| Stack | Price | Best for |
|---|---|---|
| **xAMP (preinstalled)** | Free | Out-of-the-box use, custom UI, 50k stations, AirPlay 2, B&O conversion tuning |
| Volumio | Free / €30 | Most popular Pi audiophile OS |
| Moode Audio | Free | Pure audiophile, deep DSP, Camilla DSP integrated |
| piCorePlayer + LMS | Free | Squeezebox / Lyrion ecosystem |
| RoPieee + Roon | $130/yr | Roon Ready endpoint |
| HQPlayer NAA | €230 | Audiophile upsampling holy grail |

To switch: power down, pull the SD card, flash a different image, reinsert.
Most options auto-detect the HiFiBerry Beocreate HAT.

### Why this is a great buy

1. **Genuinely custom build.** Mini-ITX chassis + 600W SFF PSU + Pod Bay 3 power management + HiFiBerry Beocreate + Pi 4 + handwritten xAMP stack. Hours of build and integration work you don't have to do.
2. **Better power than typical Pi audio.** Dedicated regulated 5VDC from an 80 Plus Gold ATX supply plus a hardware watchdog auto-reset. Cleaner than any wall-wart.
3. **B&O conversion-ready out of the box.** If you're rebuilding a Beolab 5000/6000/8000/MS150 with the Beocreate HAT, this saves you weeks of integration work.
4. **AirPlay 2 from your iPhone**, MPD for everything else, seamless switching — both work, no compromises.
5. **Open architecture.** All software components have public source, you're not locked into any single vendor.

### Shipping & Returns

- Ships within 2 business days of cleared payment
- Insured shipping included
- Returns accepted within 14 days for any reason

### Pricing

`<TBD: target sale price>`

---

A **Salient Concepts** small-batch audiophile build. Custom hardware paired with a fully open-source software baseline, designed for hands-on owners comfortable with command-line and DSP tooling — ready to tune to your specific speakers and listening room. Each unit ships as a complete working baseline; ongoing customization draws on the broader open-source ecosystem (HiFiBerry, BeoCreate2, MPD, shairport-sync).

*Sold as-is, no warranty implied or expressed. Questions: via your eBay message thread.*
