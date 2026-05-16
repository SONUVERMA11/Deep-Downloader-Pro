"""
DEEP DOWNLOADR — Filename Sanitizer
Strips illegal characters, normalizes Unicode, and enforces length limits.
"""

from __future__ import annotations

import os
import re
import unicodedata


# Characters illegal in Windows/macOS/Linux filenames
_ILLEGAL_CHARS = re.compile(r'[/\\:*?"<>|]')
_MULTI_SPACES = re.compile(r"\s{2,}")
_TRAILING_DOTS = re.compile(r"\.+$")
_LEADING_DOTS = re.compile(r"^\.+")

MAX_FILENAME_LENGTH = 200


def sanitize_filename(
    name: str,
    max_length: int = MAX_FILENAME_LENGTH,
    replace_char: str = "_",
) -> str:
    """
    Sanitize a filename for safe use across all platforms.
    
    - Strips Windows-illegal chars: / \\ : * ? " < > |
    - Normalizes Unicode (NFC form)
    - Collapses multiple spaces
    - Trims to max_length characters (preserving extension)
    - Removes leading/trailing dots and spaces
    """
    if not name:
        return "untitled"

    # Normalize Unicode
    name = unicodedata.normalize("NFC", name)

    # Replace illegal characters
    name = _ILLEGAL_CHARS.sub(replace_char, name)

    # Collapse multiple spaces/underscores
    name = _MULTI_SPACES.sub(" ", name)

    # Remove leading/trailing dots and whitespace
    name = _TRAILING_DOTS.sub("", name)
    name = _LEADING_DOTS.sub("", name)
    name = name.strip()

    # Separate extension for length trimming
    base, ext = os.path.splitext(name)
    available = max_length - len(ext)

    if len(base) > available:
        base = base[:available].rstrip()

    result = base + ext

    # Final safety check
    if not result or result in (".", ".."):
        return "untitled"

    return result


def generate_filename(
    template: str,
    metadata: dict,
    ext: str = "mp4",
) -> str:
    """
    Generate filename from a template pattern.
    
    Available placeholders:
    - {title}
    - {uploader}
    - {upload_date}
    - {resolution}
    - {id}
    - {ext}
    - {playlist_index}
    - {playlist_title}
    """
    placeholders = {
        "title": metadata.get("title", "Untitled"),
        "uploader": metadata.get("uploader", "Unknown"),
        "upload_date": metadata.get("upload_date", ""),
        "resolution": metadata.get("resolution", ""),
        "id": metadata.get("id", ""),
        "ext": ext,
        "playlist_index": str(metadata.get("playlist_index", "")),
        "playlist_title": metadata.get("playlist_title", ""),
    }

    result = template
    for key, value in placeholders.items():
        result = result.replace(f"{{{key}}}", str(value))

    return sanitize_filename(result)
