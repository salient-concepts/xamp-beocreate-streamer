# xAMP Beocreate Streamer

Custom audiophile network streamer built on the **HiFiBerry Beocreate
4-channel amplifier HAT** + Raspberry Pi 4, housed in a one-of-one custom
mini-ITX chassis with factory-engraved xAMP branding.

A **Salient Concepts** small-batch build.

---

## Restorable SD card image

The as-shipped image (~1.4 GB compressed, ~6.5 GB uncompressed) is published
on the [Releases page](https://github.com/salient-concepts/xamp-beocreate-streamer/releases/latest).
Includes firstboot autoexpand. See the release notes for flash instructions
and SHA-256 verification.

---

## What's here

```
build/                  Build + ship prep scripts
docs/
  ebay_listing_copy.md  Listing copy for the sale
  LESSONS_LEARNED.md    Hard-won development notes (READ FIRST)
etc/                    System config (mpd.conf, shairport-sync, systemd units, brand.conf)
opt/streamer-webapp/    aiohttp webapp (player UI + DSP control + auto-resume)
usr/local/sbin/         Helper scripts (DSP init, AirPlay event hook)
```

## Hardware

| | |
|---|---|
| Compute | Raspberry Pi 4 Model B Rev 1.4, 4 GB |
| DSP / amp HAT | HiFiBerry Beocreate 4-channel — ADAU1452 DSP + PCM5122 DAC + dual TAS5754M class-D |
| Power supply | SilverStone SX600-G (600 W SFX, 80 Plus Gold, modular) |
| ATX adapter | Pod Bay 3 Mini ATX PSU II (early revision, hard power-switch only — see LESSONS_LEARNED §4) |
| Chassis | GOOHEE A99 mini-ITX (acrylic + wood, factory laser-engraved xAMP) — 8.87 × 9.92 × 8.05 in |

## Software stack

- Pi OS Trixie (aarch64)
- MPD with `format "48000:24:2"` forced output (matches DSP core rate)
- shairport-sync 5.0.2 + nqptp (AirPlay 2 receiver, built from source)
- Custom aiohttp web app on port 8081 — Player / Stations / About / Settings
- 50,000+ internet radio stations via radio-browser.info
- Curated audiophile featured-stations list (Radio Paradise FLAC × 4, Linn, Naim, SomaFM, BBC, etc.)
- DSP control via sigmatcpserver on port 8086 (BeoCreate2 / SigmaStudio compatible)
- Custom `xamp-dsp-init` runs a 2-pass reset + install + clear at boot with checksum verify (see LESSONS_LEARNED §1)

## Boot sequence

1. Pi OS boots
2. `sigmatcp.service` brings up the DSP TCP control server (port 8086)
3. `dsp-clear-filters.service` → `xamp-dsp-init` performs 2-pass DSP init,
   verifies checksum, retries on mismatch (~30–60 s)
4. `mpd.service` starts (depends on dsp-clear-filters)
5. `streamer-webapp.service` starts (port 8081)
6. `shairport-sync.service` advertises AirPlay 2 endpoint

## Before troubleshooting audio

Read [`docs/LESSONS_LEARNED.md`](docs/LESSONS_LEARNED.md). Most "weird"
behaviors observed during development have a known cause and a documented
fix or rule. Especially:

- Section 1: cold-boot DSP race (continuous noise)
- Section 2: DON'T use MPD hardware mixer
- Section 3: 48 kHz force REQUIRED, but NOT with SoX VHQ
- Section 4: front button is hard power switch, not soft signal
- Section 7: diagnostic flow that worked

## Listing

[`docs/ebay_listing_copy.md`](docs/ebay_listing_copy.md) — eBay copy for
the sale.
