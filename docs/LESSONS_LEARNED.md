# xAMP Beocreate Streamer — Lessons Learned

Build notes captured during May 2026 development. Anchor for future maintenance
and second-unit builds.

---

## 1. Cold-boot DSP race condition (NOISY AUDIO)

**Symptom:** After every cold boot (full AC power loss → DSP loses RAM, not
just a Pi soft reboot), audio came up with continuous low-level noise plus
intermittent crackle/pops on every station, independent of stream sample
rate. Pause MPD → dead silence (proves digital-path origin, not amp/EMI).

**Root cause:** `dsptoolkit install-profile` talks to the DSP through the
running `sigmatcpserver` over TCP/8086. On cold boot, sigmatcpserver also
runs its own startup-time checksum probes against DSP memory. These two
streams of SPI writes/reads race, and sigmatcpserver caught a mid-install
state in its logs:

```
sigmatcpserver: WARNING: MD5 checksum mismatch:
  XML=A864F3AC2C7B30085E10DBECB145EE2D
  memory=6927FE1248E4C8F16451899A53913802
sigmatcpserver: ERROR: checksums do not match, aborting
```

`A864...EE2D` is the expected XML profile checksum; `6927...3802` is a
recurring partial-write fingerprint that appears on every cold boot
mid-install. The install eventually completes and `get-checksum` matches
the XML — **but the DSP is left in an audibly noisy steady state.**

**Fix:** A single reset + install + clear with a final checksum-match
verify is **NOT sufficient**. Empirically a single pass can report
`checksum MATCH` while audio still has noise. The verified-clean approach is:

- Wait for sigmatcpserver to be responsive on tcp/8086
- 5 s settle so sigmatcpserver finishes its own initial scan
- **Two full passes** of `reset → install → clear-iir-filters`, separated
  by a 5 s settle, each verified by `get-checksum`
- Up to 3 retries per pass on checksum mismatch

Implemented as [`/usr/local/sbin/xamp-dsp-init`](../usr/local/sbin/xamp-dsp-init), invoked from
[`dsp-clear-filters.service`](../etc/systemd/system/dsp-clear-filters.service)
with `After=sigmatcp.service`, `Requires=sigmatcp.service`,
`Before=mpd.service`, `TimeoutStartSec=120`.

Verified across two power-cycle tests: 1-pass → noisy on first listen;
2-pass → clean on first listen.

Cost: ~30–60 s extra boot time before MPD starts. Acceptable for a sale unit.

---

## 2. MPD mixer architecture — DO NOT use hardware mixer

**What I tried (and reverted):** Switching MPD's `audio_output` block to
`mixer_type "hardware"` with `mixer_control "DSPVolume"`, expecting the
DSP to do the volume attenuation losslessly at its 28-bit accumulator
depth.

**What went wrong:** ALSA's `DSPVolume` mixer control only addresses the
DSP's Front L/R **input gain**. The active 4-way DSP profile routes audio
through paths that **bypass that register entirely**. Verified by setting
DSPVolume to 0 (−90 dB) — audio remained at full output level.

**Lesson:** MPD `mixer_type "software"` is the correct choice for this
build. The 4-way Beocreate profile has its own `volumeControlRegister`
(register 542 per the profile metadata), but it's not exposed via the
kernel ALSA mixer that MPD can drive. MPD's 24-bit software volume on
this stream content gives more dynamic range than human hearing anyway.

---

## 3. Sample-rate forcing — required, but DON'T use SoX VHQ

**Discovery:** The 4-way DSP profile is compiled for **48 kHz core rate**.
Almost every curated station is **44.1 kHz** native (every Radio Paradise
FLAC, every SomaFM, KEXP, WFMU, ABC, Klassik, HD Baroque). Only France
Musique HiFi and FIP HiFi are 48 kHz.

With MPD's default `auto_resample "no"`, each station change reopens the
I2S clock at the new rate and the DSP's PLL has to re-lock — produces a
brief pop on every station change.

**Fix:** Force MPD to always emit 48 kHz:

```
audio_output {
    type      "alsa"
    name      "HiFiBerry"
    device    "hw:0,0"
    mixer_type "software"
    format    "48000:24:2"
}
```

**Important:** Do NOT add `samplerate_converter "soxr very high"`. Tested
A/B — SoX VHQ sounded **worse** per user blind listen. MPD's default
resampler (libsamplerate) is the right choice for this build. The Pi 4's
CPU runs SoX VHQ comfortably (~4% MPD CPU) but the perceived output is
worse — possibly pre-/post-ringing artifacts.

---

## 4. Pod Bay 3 Mini ATX PSU II (early revision) — button is HARD power

**What the listing was tempted to claim:** Soft-button clean shutdown via
GPIO signaling, matching Tom Tibbetts'
[Mini-ATX-PSU GitHub control scripts](https://github.com/tomtibbetts/Mini-ATX-PSU)
which use GPIO 23 (BOOT_OK out) + GPIO 24 (SHUTDOWN in).

**What's actually true:** The early-revision board Fabian purchased does
**not** signal the Pi over any GPIO. The front button toggles the PSU's
PS_ON# rail directly. Verified by hardware edge-detection probe on every
GPIO 4–27 during multiple button presses + long hold: **zero edges
captured**.

The GPIO 23/24 design came in a later revision of the PiRyte / Tom
Tibbetts board family.

**Lesson:** Don't install the `atx-psu-button` daemon on this board.
The eBay listing text describes the front button as what it actually is:
a power switch that cuts the ATX rail. Graceful shutdown is offered via
the webapp's **Shut down streamer** button (calls `sudo systemctl poweroff`,
the user waits for the Pi LED to go dark, then presses the front switch).

---

## 5. WiFi power_save defaults ON every cold boot — not currently a problem

`dmesg` on every cold boot shows:

```
brcmfmac: brcmf_cfg80211_set_power_mgmt: power save enabled
```

There is **no** NetworkManager dropin or systemd unit on the Pi that
disables it. Audio streaming on this unit isn't affected because
**eth0 is the primary route** (metric 100 vs wlan0's 600) — music goes
via wired Ethernet.

**Lesson for buyer / portable use:** If a buyer runs this unit on Wi-Fi
only, drop a `/etc/NetworkManager/conf.d/99-wifi-no-powersave.conf` with
`[connection] wifi.powersave = 2`. Worth adding to the ship_prep.sh
checklist.

---

## 6. Auto-resume on MPD stream drop

**Symptom:** "Music stops occasionally" — usually around song transitions
on FLAC streams (Radio Paradise re-segments).

**Root cause:** `mpd[N]: exception: GnuTLS recv error (-110)` — the
HTTPS stream's TLS session drops mid-segment. MPD has no built-in retry;
it goes to `stop` state and the audio goes quiet.

**Fix shipped:** Auto-resume in the webapp's `mpd_poller` thread. Tracks
"user wants playing" intent (set True by any play action, False by pause),
re-issues `c.play()` if MPD drops to stop while playing was intended,
exponential backoff (3 s → 6 → 12 → 24 → 30 s cap), backoff resets on
successful play. **AirPlay-aware** via shairport-sync hook script
(`/usr/local/sbin/xamp-airplay-event`) that POSTs `state=start|stop` to
`/api/internal/airplay`. Auto-resume only fires if AirPlay is not active.

Verified live: `mpc stop` recovers in <1 s.

---

## 7. Diagnostic flow that worked

When troubleshooting audio-quality complaints on this build, the right
order:

1. **Pause MPD and listen.** If noise stops → digital path. If continues
   → amp/power/EMI. Cuts search space in half in 30 s.
2. **Check `vcgencmd get_throttled`** and `measure_temp`. Rules out
   thermal/undervoltage.
3. **Check `cat /proc/asound/card0/pcm0p/sub0/hw_params`** for the
   actual ALSA negotiated rate/format. Compare against DSP's expected
   rate via `dsptoolkit get-samplerate`.
4. **`journalctl -u sigmatcp -b 0 | grep -iE "checksum|mismatch"`** to
   detect the cold-boot install race.
5. **Read DSP registers directly:** `dsptoolkit read-int <addr> 4` for
   528 (mute), 529 (auto-mute level), 542 (volume), 543 (volume limit),
   547 (channel select), 548 (invert mute).
6. **Probe stream rates with `ffprobe`** (from a host that can reach
   the URLs) before assuming a sample-rate-mismatch theory.

**Anti-pattern observed in this session:** I theorized 48 kHz force +
SoX VHQ would fix the pops based on rate-mismatch reasoning. User
listened — said worse. Reverted. The actual root cause was the cold-boot
DSP install race, which the rate-mismatch theory would never have caught.
Per `feedback_observe_then_fix.md`: pause MPD as step 1 to bisect the
problem space before forming theories.

---

## 8. Configuration files committed to this repo

| File | Purpose |
|---|---|
| [`etc/mpd.conf`](../etc/mpd.conf) | MPD with `format "48000:24:2"` and software mixer |
| [`etc/shairport-sync.conf`](../etc/shairport-sync.conf) | AirPlay 2 + hook script integration |
| [`etc/systemd/system/dsp-clear-filters.service`](../etc/systemd/system/dsp-clear-filters.service) | Calls `xamp-dsp-init` at boot |
| [`etc/streamer/brand.conf`](../etc/streamer/brand.conf) | Beocreate branding for the webapp |
| [`usr/local/sbin/xamp-dsp-init`](../usr/local/sbin/xamp-dsp-init) | 2-pass DSP init with checksum verify + retry |
| [`usr/local/sbin/xamp-airplay-event`](../usr/local/sbin/xamp-airplay-event) | shairport-sync session start/stop hook |
| [`opt/streamer-webapp/server.py`](../opt/streamer-webapp/server.py) | aiohttp webapp with auto-resume, AirPlay tracking, shutdown endpoint |
| [`opt/streamer-webapp/static/index.html`](../opt/streamer-webapp/static/index.html) | Webapp UI with circular Power Management cluster |
| [`build/ship_prep.sh`](../build/ship_prep.sh) | Pre-sale clean-state preparation |
| [`docs/ebay_listing_copy.md`](ebay_listing_copy.md) | Listing copy for eBay sale |
