"""Steganography detection: LSB anomaly, chi-square, palette analysis, appended data."""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class StegResult:
    source: str
    indicators: List[str] = field(default_factory=list)
    score: int = 0          # 0-100 suspicion score
    appended_bytes: int = 0
    lsb_chi_p: Optional[float] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def verdict(self) -> str:
        if not self.success:
            return "error"
        if self.score >= 70:
            return "HIGH suspicion — likely hidden data"
        if self.score >= 35:
            return "MEDIUM suspicion — anomalies detected"
        return "LOW suspicion — no clear indicators"


class StegDetector:
    """Heuristic steganography detector for PNG and BMP files (pure Python, no external deps)."""

    def detect(self, data: bytes, filename: str = "") -> StegResult:
        result = StegResult(source=filename)
        try:
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                self._analyze_png(data, result)
            elif data[:2] == b"BM":
                self._analyze_bmp(data, result)
            elif data[:3] == b"\xff\xd8\xff":
                self._analyze_jpeg(data, result)
            else:
                result.indicators.append("Not a supported image format (PNG/BMP/JPEG)")
                result.score = 0
        except Exception as exc:
            result.error = str(exc)
        return result

    # ------------------------------------------------------------------
    # PNG
    # ------------------------------------------------------------------
    def _analyze_png(self, data: bytes, result: StegResult) -> None:
        chunks = self._parse_png_chunks(data)
        chunk_types = [c[0] for c in chunks]

        # Unknown ancillary chunks can carry hidden data
        known = {b"IHDR", b"IDAT", b"IEND", b"PLTE", b"tEXt", b"zTXt",
                 b"iTXt", b"cHRM", b"gAMA", b"sRGB", b"bKGD", b"hIST",
                 b"tIME", b"pHYs", b"sBIT", b"sPLT", b"tRNS", b"iCCP"}
        unknown = [c for c in chunk_types if c not in known]
        if unknown:
            result.indicators.append(f"Unknown PNG chunks: {[c.decode(errors='replace') for c in unknown]}")
            result.score += 25

        # Text chunks can embed data
        text_chunks = [(t, d) for t, d in chunks if t in (b"tEXt", b"zTXt", b"iTXt")]
        if len(text_chunks) > 2:
            result.indicators.append(f"Unusual number of text chunks: {len(text_chunks)}")
            result.score += 10

        # Data after IEND
        iend_pos = data.rfind(b"IEND")
        if iend_pos != -1:
            trailer_start = iend_pos + 8  # "IEND" + 4-byte CRC
            if trailer_start < len(data):
                appended = len(data) - trailer_start
                result.appended_bytes = appended
                result.indicators.append(f"{appended} bytes appended after IEND")
                result.score += min(40, appended)

        # LSB chi-square on IDAT pixel data
        idat_data = b"".join(d for t, d in chunks if t == b"IDAT")
        if idat_data:
            try:
                raw = zlib.decompress(idat_data)
                p_value = self._chi_square_lsb(raw)
                result.lsb_chi_p = p_value
                if p_value > 0.05:
                    result.indicators.append(
                        f"LSB chi-square p={p_value:.3f} — pixel LSBs suspiciously uniform (steganography indicator)"
                    )
                    result.score += 30
            except zlib.error:
                pass

    def _parse_png_chunks(self, data: bytes) -> list[tuple[bytes, bytes]]:
        chunks: list[tuple[bytes, bytes]] = []
        pos = 8  # skip PNG signature
        while pos + 12 <= len(data):
            length = struct.unpack(">I", data[pos : pos + 4])[0]
            chunk_type = data[pos + 4 : pos + 8]
            chunk_data = data[pos + 8 : pos + 8 + length]
            chunks.append((chunk_type, chunk_data))
            pos += 12 + length
            if chunk_type == b"IEND":
                break
        return chunks

    # ------------------------------------------------------------------
    # BMP
    # ------------------------------------------------------------------
    def _analyze_bmp(self, data: bytes, result: StegResult) -> None:
        if len(data) < 54:
            result.error = "BMP too small to parse"
            return

        file_size = struct.unpack_from("<I", data, 2)[0]
        pixel_offset = struct.unpack_from("<I", data, 10)[0]
        width = struct.unpack_from("<I", data, 18)[0]
        height = abs(struct.unpack_from("<i", data, 22)[0])
        bit_depth = struct.unpack_from("<H", data, 28)[0]

        # Discrepancy between declared and actual file size
        if file_size != len(data):
            diff = abs(file_size - len(data))
            result.indicators.append(f"BMP declared size {file_size} vs actual {len(data)} (diff={diff})")
            result.score += 20

        # Pixel data
        pixel_data = data[pixel_offset:]
        if pixel_data and bit_depth == 24:
            p_value = self._chi_square_lsb(pixel_data)
            result.lsb_chi_p = p_value
            if p_value > 0.05:
                result.indicators.append(
                    f"LSB chi-square p={p_value:.3f} — uniform LSBs in pixel data"
                )
                result.score += 30

        result.score = min(result.score, 100)

    # ------------------------------------------------------------------
    # JPEG
    # ------------------------------------------------------------------
    def _analyze_jpeg(self, data: bytes, result: StegResult) -> None:
        # JPEG ends with FF D9; data after that is appended
        eoi = data.rfind(b"\xff\xd9")
        if eoi != -1:
            trailer_start = eoi + 2
            if trailer_start < len(data):
                appended = len(data) - trailer_start
                result.appended_bytes = appended
                result.indicators.append(f"{appended} bytes appended after JPEG EOI marker")
                result.score += min(40, appended)

        # Look for large comment (COM) markers
        pos = 2
        while pos + 4 < len(data):
            marker = data[pos : pos + 2]
            if marker == b"\xff\xd9":
                break
            if len(data) < pos + 4:
                break
            seg_len = struct.unpack_from(">H", data, pos + 2)[0]
            if marker == b"\xff\xfe":  # COM
                comment = data[pos + 4 : pos + 2 + seg_len]
                if len(comment) > 100:
                    result.indicators.append(f"Large JPEG comment segment: {len(comment)} bytes")
                    result.score += 15
            pos += 2 + seg_len

        result.score = min(result.score, 100)

    # ------------------------------------------------------------------
    # Chi-square test for LSB uniformity
    # ------------------------------------------------------------------
    def _chi_square_lsb(self, pixel_bytes: bytes) -> float:
        """Returns approximate p-value; p > 0.05 = LSBs are suspiciously uniform."""
        if len(pixel_bytes) < 100:
            return 0.0
        ones = sum(b & 1 for b in pixel_bytes)
        n = len(pixel_bytes)
        expected = n / 2
        chi2 = ((ones - expected) ** 2 + ((n - ones) - expected) ** 2) / expected
        # Approximate p-value for chi2 with 1 dof using complementary error function
        return self._chi2_p(chi2, df=1)

    @staticmethod
    def _chi2_p(chi2: float, df: int = 1) -> float:
        """Approximate survival function P(X > chi2) for chi-squared with df degrees of freedom."""
        # Use regularised incomplete gamma approximation (df=1 only)
        if df == 1:
            # P = erfc(sqrt(chi2/2))
            x = math.sqrt(chi2 / 2)
            return StegDetector._erfc(x)
        return 0.0

    @staticmethod
    def _erfc(x: float) -> float:
        """Complementary error function approximation (Abramowitz & Stegun 7.1.26)."""
        if x < 0:
            return 2.0 - StegDetector._erfc(-x)
        t = 1.0 / (1.0 + 0.3275911 * x)
        poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
        return poly * math.exp(-(x * x))
