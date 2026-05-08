"""File forensics: magic-byte identification, entropy, string extraction, hex dump."""

from __future__ import annotations

import math
import os
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# Magic-byte signatures: (offset, bytes) -> (mime, description)
_MAGIC: list[tuple[int, bytes, str, str]] = [
    # offset, signature, mime, label
    (0, b"\x89PNG\r\n\x1a\n", "image/png", "PNG image"),
    (0, b"\xff\xd8\xff", "image/jpeg", "JPEG image"),
    (0, b"GIF87a", "image/gif", "GIF87 image"),
    (0, b"GIF89a", "image/gif", "GIF89 image"),
    (0, b"BM", "image/bmp", "BMP image"),
    (0, b"RIFF", "audio/wav", "RIFF/WAV audio"),  # refined below
    (0, b"\x00\x00\x01\x00", "image/ico", "ICO icon"),
    (0, b"%PDF-", "application/pdf", "PDF document"),
    (0, b"PK\x03\x04", "application/zip", "ZIP archive"),
    (0, b"PK\x05\x06", "application/zip", "ZIP archive (empty)"),
    (0, b"Rar!\x1a\x07\x00", "application/x-rar", "RAR archive v4"),
    (0, b"Rar!\x1a\x07\x01", "application/x-rar", "RAR archive v5"),
    (0, b"\x1f\x8b", "application/gzip", "Gzip archive"),
    (0, b"BZh", "application/bzip2", "Bzip2 archive"),
    (0, b"\xfd7zXZ\x00", "application/xz", "XZ archive"),
    (0, b"7z\xbc\xaf'\x1c", "application/x-7z", "7-Zip archive"),
    (0, b"\xca\xfe\xba\xbe", "application/x-mach", "Mach-O fat binary"),
    (0, b"\xcf\xfa\xed\xfe", "application/x-mach", "Mach-O 64-bit LE"),
    (0, b"\xce\xfa\xed\xfe", "application/x-mach", "Mach-O 32-bit LE"),
    (0, b"\x7fELF", "application/x-elf", "ELF binary"),
    (0, b"MZ", "application/x-pe", "PE/DOS executable"),
    (0, b"#!/", "text/x-script", "Shell script"),
    (0, b"#!", "text/x-script", "Script"),
    (0, b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "application/msoffice", "MS Office document (OLE2)"),
    (0, b"\x50\x4b\x03\x04\x14\x00\x06\x00", "application/xlsx", "MS Office Open XML (OOXML)"),
    (0, b"SQLite format 3", "application/x-sqlite3", "SQLite database"),
    (0, b"\x00\x01\x00\x00Standard", "application/x-access", "MS Access database"),
    (0, b"OggS", "audio/ogg", "OGG audio"),
    (0, b"fLaC", "audio/flac", "FLAC audio"),
    (0, b"ID3", "audio/mpeg", "MP3 audio (ID3)"),
    (0, b"\xff\xfb", "audio/mpeg", "MP3 audio"),
    (0, b"\x00\x00\x00\x18ftyp", "video/mp4", "MP4 video"),
    (4, b"ftyp", "video/mp4", "MP4 video"),
    (0, b"\x1aE\xdf\xa3", "video/webm", "WebM/MKV video"),
    (0, b"\x30\x26\xb2\x75\x8e\x66\xcf\x11", "video/wmv", "WMV video"),
    (0, b"FORM", "audio/aiff", "AIFF audio"),
    (0, b"<?xml", "text/xml", "XML document"),
    (0, b"<html", "text/html", "HTML document"),
    (0, b"<HTML", "text/html", "HTML document"),
    (0, b"{\n", "application/json", "JSON document"),
    (0, b"{\"", "application/json", "JSON document"),
]


@dataclass
class FileInfo:
    path: str
    size: int
    mime: str
    description: str
    entropy: float
    printable_strings: List[str] = field(default_factory=list)
    hex_preview: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def entropy_label(self) -> str:
        if self.entropy < 1.0:
            return "very low (mostly zeros/padding)"
        if self.entropy < 3.5:
            return "low (text or structured data)"
        if self.entropy < 6.0:
            return "medium (mixed content)"
        if self.entropy < 7.2:
            return "high (compressed or encoded)"
        return "very high (encrypted or compressed)"


class FileAnalyzer:
    """Identifies file types, computes entropy, extracts strings, and produces hex previews."""

    def analyze(
        self,
        source: "str | bytes | os.PathLike",
        max_strings: int = 30,
        min_string_len: int = 4,
        hex_bytes: int = 256,
    ) -> FileInfo:
        path_str = ""
        try:
            if isinstance(source, (str, os.PathLike)):
                p = Path(source)
                path_str = str(p)
                data = p.read_bytes()
            else:
                data = bytes(source)

            size = len(data)
            mime, description = self._identify(data)
            entropy = self._entropy(data)
            strings = self._extract_strings(data, min_string_len, max_strings)
            hex_preview = self._hex_dump(data[:hex_bytes])

            return FileInfo(
                path=path_str,
                size=size,
                mime=mime,
                description=description,
                entropy=entropy,
                printable_strings=strings,
                hex_preview=hex_preview,
            )
        except Exception as exc:
            return FileInfo(
                path=path_str,
                size=0,
                mime="unknown",
                description="unknown",
                entropy=0.0,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    def _identify(self, data: bytes) -> tuple[str, str]:
        for offset, sig, mime, label in _MAGIC:
            end = offset + len(sig)
            if len(data) >= end and data[offset:end] == sig:
                # Distinguish WAV from generic RIFF
                if mime == "audio/wav" and len(data) >= 12 and data[8:12] == b"WAVE":
                    return "audio/wav", "WAV audio"
                if mime == "audio/wav":
                    return "application/riff", "RIFF data"
                return mime, label
        # Heuristic: if high proportion of printable ASCII → text
        if data:
            printable_ratio = sum(0x20 <= b < 0x7F or b in (9, 10, 13) for b in data[:512]) / min(512, len(data))
            if printable_ratio > 0.80:
                return "text/plain", "ASCII/UTF-8 text"
        return "application/octet-stream", "Binary data (unknown)"

    def _entropy(self, data: bytes) -> float:
        if not data:
            return 0.0
        freq = [0] * 256
        for b in data:
            freq[b] += 1
        n = len(data)
        return -sum((c / n) * math.log2(c / n) for c in freq if c)

    def _extract_strings(self, data: bytes, min_len: int, limit: int) -> list[str]:
        results: list[str] = []
        current: list[int] = []
        for b in data:
            if 0x20 <= b < 0x7F:
                current.append(b)
            else:
                if len(current) >= min_len:
                    results.append(bytes(current).decode("ascii"))
                    if len(results) >= limit:
                        break
                current = []
        if current and len(current) >= min_len and len(results) < limit:
            results.append(bytes(current).decode("ascii"))
        return results

    def _hex_dump(self, data: bytes) -> str:
        lines: list[str] = []
        for i in range(0, len(data), 16):
            chunk = data[i : i + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            asc_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
            lines.append(f"{i:08x}  {hex_part:<47}  |{asc_part}|")
        return "\n".join(lines)
