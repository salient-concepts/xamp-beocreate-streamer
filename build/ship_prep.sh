#!/usr/bin/env bash
# ship_prep.sh — factory-reset the xAMP Beocreate before shipping.
# Wipes saved WiFi credentials, user-side streamer state, AirPlay pairing,
# shell history, journal entries, then reboots into Comitup HOTSPOT mode
# for first-boot WiFi onboarding by the buyer.
#
# DSP profile + EEPROM + brand config + audiophile tuning are PRESERVED, but
# the DSP is reset + the IIR filter slots are cleared so the buyer's first
# audio playthrough is from a known-clean state (no leftover filter coloration
# from seller-side profile experimentation).
#
# Run on the unit:    CONFIRM=yes bash /home/pi/ship_prep.sh

set -euo pipefail

if [ "${CONFIRM:-}" != "yes" ]; then
  cat <<MSG
ship_prep.sh — wipes user state and reboots into HOTSPOT mode.

To proceed:    CONFIRM=yes bash /home/pi/ship_prep.sh

Wiped:    saved WiFi creds · streamer favorites · MPD state · shell history
          shairport-sync AirPlay pairings · journalctl logs · /tmp temp files
Reset:    MPD volume → 50% · DSP filter slots → cleared (re-applies profile)
Preserved: DSP profile XML · EEPROM · /etc/streamer/brand.conf · audio tuning
MSG
  exit 1
fi

DT=/opt/dsptools/venv/bin/dsptoolkit

echo "[ship_prep] stopping audio + web services..."
sudo systemctl stop streamer-webapp mpd shairport-sync 2>/dev/null || true

echo "[ship_prep] DSP reset → re-install profile → clear IIR filters..."
# Brings DSP back to a known-clean state so the buyer's first playback is not
# colored by leftover filter slot values from seller-side profile testing.
sudo "$DT" reset            2>/dev/null | tail -1 || true
sudo "$DT" install-profile /var/lib/hifiberry/dspprogram.xml 2>/dev/null | tail -1 || true
sudo "$DT" clear-iir-filters 2>/dev/null | tail -1 || true

echo "[ship_prep] wiping saved WiFi credentials..."
sudo rm -f /etc/NetworkManager/system-connections/*.nmconnection
sudo nmcli connection reload 2>/dev/null || true

# Wipe Comitup's persisted hotspot suffix so each shipped unit broadcasts a
# fresh random "xAMP-Beocreate-NNN" rather than carrying a stale id across
# factory resets. Without this, every refurbished/demo unit comes up with
# the same SSID and SSID collisions happen if a buyer ever owns two.
sudo rm -f /var/lib/comitup/comitup.json

echo "[ship_prep] wiping streamer user state..."
sudo rm -f /var/lib/streamer/favorites.json
sudo rm -f /var/lib/streamer/user_stations.json
sudo rm -rf /var/lib/streamer/cover_art_cache/*  2>/dev/null || true

echo "[ship_prep] wiping shairport-sync AirPlay pairings + caches..."
sudo rm -rf /var/lib/shairport-sync/*  2>/dev/null || true
sudo rm -rf /var/cache/shairport-sync/* 2>/dev/null || true
sudo rm -f /tmp/shairport-sync-metadata 2>/dev/null || true

echo "[ship_prep] wiping MPD state + seeding safe default volume..."
sudo rm -f /var/lib/mpd/state /var/lib/mpd/sticker.sql
# Start MPD long enough to write a fresh state file with vol=50, then stop again
sudo systemctl start mpd
sleep 2
mpc volume 50 >/dev/null 2>&1 || true
sudo systemctl stop mpd  # forces MPD to flush state to disk on exit

echo "[ship_prep] wiping shell history & temp files..."
sudo rm -f /home/pi/.bash_history /root/.bash_history
sudo rm -f /tmp/sine.wav /tmp/song.wav /tmp/*.py /tmp/*.html /tmp/*.css /tmp/*.js 2>/dev/null || true
sudo rm -f /tmp/build_airplay2.sh /tmp/airplay2-build.log 2>/dev/null || true
sudo rm -rf /tmp/airplay2_build 2>/dev/null || true
history -c 2>/dev/null || true

echo "[ship_prep] vacuuming journalctl (scrubs WiFi PSK fragments + boot logs)..."
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s 2>&1 | tail -2

echo "[ship_prep] resetting hostname to xamp-beocreate (predictable mDNS)..."
echo "xamp-beocreate" | sudo tee /etc/hostname > /dev/null
sudo hostnamectl set-hostname xamp-beocreate 2>/dev/null || true
sudo sed -i "s|^127\.0\.1\.1.*|127.0.1.1\txamp-beocreate|" /etc/hosts

echo "[ship_prep] verifying critical services still enabled..."
for s in mpd streamer-webapp sigmatcp dsp-clear-filters cpu-governor comitup nqptp shairport-sync; do
  state=$(systemctl is-enabled "$s" 2>/dev/null || echo "missing")
  printf "  %-25s %s\n" "$s" "$state"
done

echo
echo "[ship_prep] DONE. Rebooting in 5s into HOTSPOT mode..."
echo "  Buyer connects to:  xAMP-Beocreate-<nnn> (open AP)"
echo "  Captive portal:     http://10.41.0.1/"
echo "  After WiFi setup:   http://xamp-beocreate.local:8081/"
sleep 5
sudo reboot
