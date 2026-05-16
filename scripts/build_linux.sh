#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# DEEP DOWNLOADR — Linux Build Script
# Builds .AppImage, .deb, and .rpm with bundled binaries
# ═══════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUNDLED_DIR="$PROJECT_DIR/bundled"

echo "🔧 DEEP DOWNLOADR — Linux Build"
echo "================================="

# Step 1: Check prerequisites
echo "📋 Checking prerequisites..."
command -v cargo >/dev/null 2>&1 || { echo "❌ Rust/Cargo required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }

# Step 2: Bundle FFmpeg
echo "📦 Bundling FFmpeg..."
if [ ! -f "$BUNDLED_DIR/ffmpeg" ]; then
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" -o /tmp/ffmpeg.tar.xz
    elif [ "$ARCH" = "aarch64" ]; then
        curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz" -o /tmp/ffmpeg.tar.xz
    fi
    tar xf /tmp/ffmpeg.tar.xz -C /tmp/
    cp /tmp/ffmpeg-*-static/ffmpeg "$BUNDLED_DIR/ffmpeg"
    cp /tmp/ffmpeg-*-static/ffprobe "$BUNDLED_DIR/ffprobe"
    chmod +x "$BUNDLED_DIR/ffmpeg" "$BUNDLED_DIR/ffprobe"
    rm -rf /tmp/ffmpeg*
fi

# Step 3: Bundle aria2c
echo "📦 Bundling aria2c..."
if [ ! -f "$BUNDLED_DIR/aria2c" ]; then
    ARIA2_PATH=$(which aria2c 2>/dev/null || true)
    if [ -n "$ARIA2_PATH" ]; then
        cp "$ARIA2_PATH" "$BUNDLED_DIR/aria2c"
        chmod +x "$BUNDLED_DIR/aria2c"
    else
        echo "   ⚠️  Install aria2: sudo apt install aria2 / sudo dnf install aria2"
    fi
fi

# Step 4: Build Python backend
echo "🐍 Building Python backend..."
cd "$PROJECT_DIR"
python3 -m pip install pyinstaller --quiet 2>/dev/null || true
python3 -m PyInstaller \
    --onefile \
    --name deep-downloadr-backend \
    --hidden-import backend.core.downloader \
    --hidden-import backend.core.hls_engine \
    --hidden-import backend.core.torrent_engine \
    --hidden-import backend.core.telegram_client \
    --hidden-import backend.core.metadata_engine \
    --hidden-import uvicorn \
    backend/api/server.py 2>/dev/null || echo "   ⚠️  PyInstaller build skipped"

# Step 5: Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd "$PROJECT_DIR"
npm install --silent

# Step 6: Build Tauri app
echo "🏗️  Building Tauri application..."
npm run tauri build

echo ""
echo "✅ Build complete!"
echo "   📁 Output: $PROJECT_DIR/src-tauri/target/release/bundle/"
echo "   📦 .deb:      src-tauri/target/release/bundle/deb/"
echo "   📦 .rpm:      src-tauri/target/release/bundle/rpm/"
echo "   📦 .AppImage: src-tauri/target/release/bundle/appimage/"
