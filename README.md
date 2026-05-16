# DEEP DOWNLOADR ⚡

A professional-grade, all-in-one media downloader and torrent client for macOS and Linux. Built with a native Rust/Tauri frontend and a powerful Python backend.

![DEEP DOWNLOADR UI](artifacts/ui_walkthrough.webp)

## Features

- **Universal Media Extraction**: Download from YouTube, Instagram, Twitter, and thousands of other sites using an embedded `yt-dlp` engine.
- **HLS/M3U8 Streaming**: Full support for recording live streams and downloading encrypted HLS segments with AES-128 decryption.
- **Torrent Client**: Built-in multi-segment downloading, DHT, PEX, and LSD support via `libtorrent-rasterbar`. Search directly across TPB, YTS, and Nyaa.
- **Telegram Integration**: Browse and download media directly from Telegram chats, channels, and groups with smart resume capabilities.
- **Smart Resume System**: Industry-first 5-method detection system (.deepdl sidecars, unique IDs, size matching, name matching, and timestamp fingerprinting) ensures interrupted downloads always resume.
- **Deduplication**: Automatically detects duplicates across all sources using sampled SHA256 hashing.
- **Zero-Cost OSS Stack**: 100% free and open-source. No paid APIs, no SaaS services, no licensing fees.

## Technology Stack

- **UI Layer**: Tauri 2.0 (Rust backend + React/TypeScript frontend)
- **Styling**: Vanilla CSS with custom design system (4 themes including Frosted Glass)
- **Download Core**: Python 3.11+, FastAPI, SQLAlchemy, `yt-dlp` wrapper
- **Speed Engine**: `aria2c` multi-connection downloader
- **Media Processing**: Static FFmpeg builds for muxing and metadata

## Development Setup

### Prerequisites

- Rust / Cargo
- Node.js (v18+)
- Python 3.11+
- FFmpeg & aria2c (system level or bundled)

### Getting Started

1. Clone the repository and navigate to the project root:
   ```bash
   cd deep-downloadr
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Install backend dependencies (recommended in a virtual environment):
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

4. Run in development mode:
   ```bash
   npm run tauri dev
   ```

## Building for Production

We provide automated scripts to bundle all dependencies (FFmpeg, aria2c, Python) into a standalone zero-install application.

**For macOS (.dmg)**
```bash
./scripts/build_macos.sh
```

**For Linux (.deb, .rpm, .AppImage)**
```bash
./scripts/build_linux.sh
```

## Architecture

DEEP DOWNLOADR uses a multi-process architecture:
1. **Tauri Main Process (Rust)**: Manages OS windows, native menus, and lifecycle.
2. **Webview Process (React)**: Renders the highly-responsive UI.
3. **Backend Process (Python)**: Runs as an invisible subprocess, exposing a fast local API over HTTP and WebSockets for real-time progress.

## License

MIT License. See `LICENSE` for details.
