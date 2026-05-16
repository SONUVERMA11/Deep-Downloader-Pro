#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
# DEEP DOWNLOADR — macOS Build Script
# Builds .dmg with bundled FFmpeg, aria2c, and Python backend
# ═══════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUNDLED_DIR="$PROJECT_DIR/bundled"

echo "🔧 DEEP DOWNLOADR — macOS Build"
echo "================================"

# Step 1: Check prerequisites
echo "📋 Checking prerequisites..."
command -v cargo >/dev/null 2>&1 || { echo "❌ Rust/Cargo required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 required"; exit 1; }

# Step 2: Bundle FFmpeg (static build)
echo "📦 Bundling FFmpeg..."
if [ ! -f "$BUNDLED_DIR/ffmpeg" ]; then
    echo "   Downloading static FFmpeg for macOS..."
    curl -L "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip" -o /tmp/ffmpeg.zip
    unzip -o /tmp/ffmpeg.zip -d "$BUNDLED_DIR/"
    chmod +x "$BUNDLED_DIR/ffmpeg"
    rm /tmp/ffmpeg.zip
fi

# Step 3: Bundle aria2c
echo "📦 Bundling aria2c..."
if [ ! -f "$BUNDLED_DIR/aria2c" ]; then
    if command -v brew >/dev/null 2>&1; then
        cp "$(brew --prefix aria2)/bin/aria2c" "$BUNDLED_DIR/aria2c" 2>/dev/null || \
        echo "   ⚠️  Install aria2 via: brew install aria2"
    fi
fi

# Step 4: Build Python backend as standalone binary
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
echo "   📀 .dmg: src-tauri/target/release/bundle/dmg/"
