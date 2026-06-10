#!/usr/bin/env bash
# PecanPi Streamer — shairport-sync with AirPlay 2 build
# Reproducible recipe for the product image. Idempotent: safe to re-run.
#
# Builds:
#   1. nqptp           (companion PTP timing daemon, required by AirPlay 2)
#   2. shairport-sync  (with --with-airplay-2 + soxr + alsa + avahi + metadata)
#
# Targets: Raspberry Pi OS Trixie aarch64. Pi 3B compile time ~25 min total.

set -euo pipefail

BUILD_DIR=/tmp/airplay2_build
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

log() { echo "[$(date +%H:%M:%S)] $*" >&2; }

# ── 1. Build dependencies ────────────────────────────────────────────────────
log "Refreshing apt cache (stale metadata 404s on point-release debs)"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq

log "Installing build dependencies"
sudo DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends \
    build-essential git autoconf automake libtool pkg-config xxd \
    libpopt-dev libconfig-dev libasound2-dev \
    libavahi-client-dev libssl-dev libsoxr-dev \
    libplist-dev libplist-utils libsodium-dev libgcrypt-dev \
    libavutil-dev libavcodec-dev libavformat-dev \
    uuid-dev libdaemon-dev

# ── 2. nqptp (PTP timing) ────────────────────────────────────────────────────
if [ ! -d nqptp ]; then
    log "Cloning nqptp"
    git clone --depth 1 https://github.com/mikebrady/nqptp.git
fi
cd nqptp
log "Building nqptp"
autoreconf -fi
./configure --with-systemd-startup
make -j2
sudo make install
sudo systemctl daemon-reload
sudo systemctl enable nqptp
sudo systemctl restart nqptp
sleep 1
systemctl is-active nqptp || { echo "ERROR: nqptp failed to start"; exit 1; }
log "nqptp installed and active"
cd "$BUILD_DIR"

# ── 3. Stop the apt-installed shairport-sync (we're replacing it) ────────────
log "Stopping apt-installed shairport-sync"
sudo systemctl stop shairport-sync || true

# ── 4. shairport-sync with AirPlay 2 ─────────────────────────────────────────
if [ ! -d shairport-sync ]; then
    log "Cloning shairport-sync"
    git clone --depth 1 https://github.com/mikebrady/shairport-sync.git
fi
cd shairport-sync
log "Configuring shairport-sync (AirPlay 2 build)"
autoreconf -fi
./configure \
    --sysconfdir=/etc \
    --with-alsa \
    --with-soxr \
    --with-avahi \
    --with-ssl=openssl \
    --with-systemd \
    --with-airplay-2 \
    --with-metadata
# Optional flags intentionally omitted (each pulls extra deps):
#   --with-mqtt-client     (libmosquitto-dev)
#   --with-dbus-interface  (libglib2.0-dev — installed but unused here)
#   --with-mpris-interface (libglib2.0-dev — installed but unused here)
# Re-enable if you need home-automation integration in the product image.

log "Compiling shairport-sync (this will take 15-25 minutes on Pi 3B)"
make -j2
log "Installing shairport-sync"
sudo make install
sudo systemctl daemon-reload

# Verify the new binary has AirPlay 2 support
log "Verifying AirPlay 2 support in installed binary"
/usr/local/bin/shairport-sync -V | tee /tmp/sps_version.txt
if grep -qE "AirPlay-?2" /tmp/sps_version.txt; then
    log "✓ AirPlay 2 support confirmed"
else
    echo "ERROR: AirPlay 2 not in build features" >&2
    exit 1
fi

log "Build complete. Restart shairport-sync service to load new binary."
