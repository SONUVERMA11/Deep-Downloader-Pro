"""
DEEP DOWNLOADR — Torrent Search
Multi-index search across apibay (TPB), 1337x, YTS, and Nyaa.
Results are merged, deduplicated, and sorted by seeds.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger("deep-downloadr.torrent_search")

TIMEOUT = aiohttp.ClientTimeout(total=10)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
}


@dataclass
class TorrentResult:
    name: str
    size: int  # bytes
    seeds: int
    leechers: int
    magnet: str
    info_hash: str
    source: str
    uploader: str = ""
    date: str = ""
    category: str = ""


def _format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size_bytes) < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def _make_magnet(info_hash: str, name: str) -> str:
    trackers = [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.demonii.com:1337/announce",
        "udp://tracker.openbittorrent.com:6969/announce",
        "udp://exodus.desync.com:6969/announce",
    ]
    tr = "&".join(f"tr={t}" for t in trackers)
    return f"magnet:?xt=urn:btih:{info_hash}&dn={quote_plus(name)}&{tr}"


# ──────────────────────────────────────────────
# apibay.org (The Pirate Bay API)
# ──────────────────────────────────────────────

async def search_apibay(query: str, category: str | None = None) -> list[TorrentResult]:
    """Search The Pirate Bay via apibay.org JSON API."""
    results = []
    try:
        url = f"https://apibay.org/q.php?q={quote_plus(query)}"
        if category:
            cat_map = {"movies": "207", "tv": "205", "music": "101", "software": "300", "games": "400"}
            cat = cat_map.get(category.lower(), "")
            if cat:
                url += f"&cat={cat}"

        async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
            async with session.get(url) as resp:
                data = await resp.json(content_type=None)

        if isinstance(data, list):
            for item in data:
                if item.get("name") == "No results returned":
                    break
                info_hash = item.get("info_hash", "")
                name = item.get("name", "")
                results.append(TorrentResult(
                    name=name,
                    size=int(item.get("size", 0)),
                    seeds=int(item.get("seeders", 0)),
                    leechers=int(item.get("leechers", 0)),
                    magnet=_make_magnet(info_hash, name),
                    info_hash=info_hash,
                    source="TPB",
                    uploader=item.get("username", ""),
                    date=item.get("added", ""),
                    category=item.get("category", ""),
                ))
    except Exception as e:
        logger.warning(f"apibay search failed: {e}")

    return results


# ──────────────────────────────────────────────
# YTS.mx (Movie API)
# ──────────────────────────────────────────────

async def search_yts(query: str) -> list[TorrentResult]:
    """Search YTS.mx official JSON API for movies."""
    results = []
    try:
        url = f"https://yts.mx/api/v2/list_movies.json?query_term={quote_plus(query)}&limit=20"
        async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
            async with session.get(url) as resp:
                data = await resp.json()

        movies = data.get("data", {}).get("movies", [])
        for movie in movies:
            for torrent in movie.get("torrents", []):
                name = f"{movie['title']} ({movie.get('year', '')}) [{torrent.get('quality', '')}] [{torrent.get('type', '')}]"
                info_hash = torrent.get("hash", "")
                results.append(TorrentResult(
                    name=name,
                    size=int(torrent.get("size_bytes", 0)),
                    seeds=int(torrent.get("seeds", 0)),
                    leechers=int(torrent.get("peers", 0)),
                    magnet=_make_magnet(info_hash, name),
                    info_hash=info_hash,
                    source="YTS",
                    date=torrent.get("date_uploaded", ""),
                    category="Movies",
                ))
    except Exception as e:
        logger.warning(f"YTS search failed: {e}")

    return results


# ──────────────────────────────────────────────
# Nyaa.si (Anime)
# ──────────────────────────────────────────────

async def search_nyaa(query: str) -> list[TorrentResult]:
    """Search Nyaa.si for anime/Japanese content via HTML scraping."""
    results = []
    try:
        url = f"https://nyaa.si/?f=0&c=0_0&q={quote_plus(query)}&s=seeders&o=desc"
        async with aiohttp.ClientSession(headers=HEADERS, timeout=TIMEOUT) as session:
            async with session.get(url) as resp:
                html = await resp.text()

        # Simple regex parsing (avoid BeautifulSoup dependency)
        rows = re.findall(r'<tr class="(?:default|success|danger)">(.*?)</tr>', html, re.DOTALL)
        for row in rows[:20]:
            cols = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cols) < 7:
                continue

            name_match = re.search(r'title="([^"]+)"', cols[1])
            magnet_match = re.search(r'href="(magnet:\?[^"]+)"', cols[2])
            hash_match = re.search(r'btih:([a-fA-F0-9]+)', cols[2]) if magnet_match else None

            if name_match and magnet_match:
                name = name_match.group(1)
                size_text = re.sub(r'<[^>]+>', '', cols[3]).strip()
                seeds = int(re.sub(r'<[^>]+>', '', cols[5]).strip() or 0)
                leechers = int(re.sub(r'<[^>]+>', '', cols[6]).strip() or 0)

                # Parse size to bytes
                size_bytes = 0
                size_match = re.match(r'([\d.]+)\s*(GiB|MiB|KiB|TiB)', size_text)
                if size_match:
                    val = float(size_match.group(1))
                    unit = size_match.group(2)
                    multipliers = {"KiB": 1024, "MiB": 1048576, "GiB": 1073741824, "TiB": 1099511627776}
                    size_bytes = int(val * multipliers.get(unit, 1))

                results.append(TorrentResult(
                    name=name,
                    size=size_bytes,
                    seeds=seeds,
                    leechers=leechers,
                    magnet=magnet_match.group(1),
                    info_hash=hash_match.group(1) if hash_match else "",
                    source="Nyaa",
                    category="Anime",
                ))
    except Exception as e:
        logger.warning(f"Nyaa search failed: {e}")

    return results


# ──────────────────────────────────────────────
# Unified Search
# ──────────────────────────────────────────────

async def search(
    query: str,
    category: str | None = None,
    min_seeds: int = 0,
) -> list[dict[str, Any]]:
    """
    Search all indexes in parallel, merge and deduplicate results.
    """
    search_tasks = [
        search_apibay(query, category),
        search_yts(query),
        search_nyaa(query),
    ]

    all_results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

    # Merge results
    all_results: list[TorrentResult] = []
    for result in all_results_lists:
        if isinstance(result, list):
            all_results.extend(result)

    # Deduplicate by info_hash
    seen: set[str] = set()
    unique: list[TorrentResult] = []
    for r in all_results:
        key = r.info_hash.lower() if r.info_hash else r.name
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Filter by min seeds
    if min_seeds > 0:
        unique = [r for r in unique if r.seeds >= min_seeds]

    # Sort by seeds descending
    unique.sort(key=lambda r: r.seeds, reverse=True)

    # Convert to dicts
    return [
        {
            "name": r.name,
            "size": r.size,
            "size_str": _format_size(r.size),
            "seeds": r.seeds,
            "leechers": r.leechers,
            "magnet": r.magnet,
            "info_hash": r.info_hash,
            "source": r.source,
            "uploader": r.uploader,
            "date": r.date,
            "category": r.category,
        }
        for r in unique[:50]  # Cap at 50 results
    ]
