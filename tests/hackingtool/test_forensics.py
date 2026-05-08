"""Tests for hackingtool forensics module (file_analyzer + steg_detector)."""

import struct
import zlib
import pytest

from hackingtool.modules.forensics.file_analyzer import FileAnalyzer, FileInfo
from hackingtool.modules.forensics.steg_detector import StegDetector, StegResult


# ---------------------------------------------------------------------------
# Helpers — build minimal valid image bytes in-process (no files on disk)
# ---------------------------------------------------------------------------

def make_png(width: int = 4, height: int = 4, bit_depth: int = 8, extra_after_iend: bytes = b"") -> bytes:
    """Build a minimal valid grayscale PNG."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, bit_depth, 0, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)

    # Raw pixel data: one filter byte per row + pixel bytes
    raw_rows = bytes([0] + [128] * width) * height
    idat = chunk(b"IDAT", zlib.compress(raw_rows))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend + extra_after_iend


def make_bmp(width: int = 4, height: int = 4) -> bytes:
    """Build a minimal valid 24-bit BMP."""
    row_size = (width * 3 + 3) & ~3
    pixel_data = bytes(row_size * height)
    pixel_offset = 54
    file_size = pixel_offset + len(pixel_data)
    header = (
        b"BM"
        + struct.pack("<I", file_size)
        + b"\x00\x00\x00\x00"
        + struct.pack("<I", pixel_offset)
        + struct.pack("<I", 40)           # DIB header size
        + struct.pack("<I", width)
        + struct.pack("<i", height)
        + struct.pack("<H", 1)            # color planes
        + struct.pack("<H", 24)           # bit depth
        + b"\x00" * 24                   # rest of DIB header
    )
    return header + pixel_data


def make_jpeg_minimal(appended: bytes = b"") -> bytes:
    """Build a tiny JPEG-like blob with SOI + EOI markers."""
    return b"\xff\xd8\xff\xe0" + struct.pack(">H", 16) + b"\x00" * 14 + b"\xff\xd9" + appended


# ---------------------------------------------------------------------------
# FileAnalyzer — identification
# ---------------------------------------------------------------------------

class TestFileAnalyzerIdentification:
    def setup_method(self):
        self.fa = FileAnalyzer()

    def test_identify_png(self):
        data = make_png()
        info = self.fa.analyze(data)
        assert info.mime == "image/png"
        assert "PNG" in info.description

    def test_identify_bmp(self):
        data = make_bmp()
        info = self.fa.analyze(data)
        assert info.mime == "image/bmp"
        assert "BMP" in info.description

    def test_identify_jpeg(self):
        data = make_jpeg_minimal()
        info = self.fa.analyze(data)
        assert info.mime == "image/jpeg"

    def test_identify_pdf(self):
        data = b"%PDF-1.4 fake content"
        info = self.fa.analyze(data)
        assert info.mime == "application/pdf"

    def test_identify_zip(self):
        data = b"PK\x03\x04" + b"\x00" * 20
        info = self.fa.analyze(data)
        assert info.mime == "application/zip"

    def test_identify_elf(self):
        data = b"\x7fELF" + b"\x00" * 60
        info = self.fa.analyze(data)
        assert info.mime == "application/x-elf"

    def test_identify_pe(self):
        data = b"MZ" + b"\x00" * 60
        info = self.fa.analyze(data)
        assert info.mime == "application/x-pe"

    def test_identify_gzip(self):
        data = b"\x1f\x8b" + b"\x00" * 20
        info = self.fa.analyze(data)
        assert info.mime == "application/gzip"

    def test_identify_text(self):
        data = b"Hello, world! This is plain ASCII text.\n"
        info = self.fa.analyze(data)
        assert info.mime == "text/plain"

    def test_identify_unknown_binary(self):
        data = bytes(range(256)) * 10
        info = self.fa.analyze(data)
        assert info.mime == "application/octet-stream"


# ---------------------------------------------------------------------------
# FileAnalyzer — entropy
# ---------------------------------------------------------------------------

class TestFileAnalyzerEntropy:
    def setup_method(self):
        self.fa = FileAnalyzer()

    def test_all_zeros_entropy_is_zero(self):
        info = self.fa.analyze(b"\x00" * 1000)
        assert info.entropy == 0.0

    def test_uniform_random_entropy_near_eight(self):
        # All 256 byte values equally represented → max entropy ≈ 8.0
        data = bytes(range(256)) * 4
        info = self.fa.analyze(data)
        assert info.entropy > 7.9

    def test_text_entropy_moderate(self):
        text = (b"the quick brown fox jumps over the lazy dog " * 20)
        info = self.fa.analyze(text)
        assert 3.0 < info.entropy < 6.0

    def test_entropy_label_very_low(self):
        info = self.fa.analyze(b"\x00" * 100)
        assert "very low" in info.entropy_label

    def test_entropy_label_very_high(self):
        data = bytes(range(256)) * 8
        info = self.fa.analyze(data)
        assert "very high" in info.entropy_label or "high" in info.entropy_label

    def test_entropy_label_low_for_text(self):
        text = b"hello world " * 50
        info = self.fa.analyze(text)
        assert "low" in info.entropy_label or "medium" in info.entropy_label


# ---------------------------------------------------------------------------
# FileAnalyzer — string extraction
# ---------------------------------------------------------------------------

class TestFileAnalyzerStrings:
    def setup_method(self):
        self.fa = FileAnalyzer()

    def test_extracts_known_string(self):
        data = b"\x00\x01" + b"HelloWorld" + b"\x00\x02"
        info = self.fa.analyze(data)
        assert "HelloWorld" in info.printable_strings

    def test_skips_short_strings(self):
        data = b"\x00\x01" + b"Hi" + b"\x00\x01" + b"LongEnoughString" + b"\x00"
        info = self.fa.analyze(data)
        assert "Hi" not in info.printable_strings
        assert "LongEnoughString" in info.printable_strings

    def test_returns_up_to_max_strings(self):
        # Embed 40 strings of length 8, separated by null bytes
        data = b"\x00".join(b"AAAAAAAA" for _ in range(40))
        info = self.fa.analyze(data, max_strings=10)
        assert len(info.printable_strings) <= 10

    def test_no_strings_in_zero_data(self):
        info = self.fa.analyze(b"\x00" * 100)
        assert info.printable_strings == []


# ---------------------------------------------------------------------------
# FileAnalyzer — hex dump
# ---------------------------------------------------------------------------

class TestFileAnalyzerHexDump:
    def setup_method(self):
        self.fa = FileAnalyzer()

    def test_hex_dump_contains_offset(self):
        info = self.fa.analyze(b"A" * 16)
        assert "00000000" in info.hex_preview

    def test_hex_dump_shows_printable_chars(self):
        info = self.fa.analyze(b"Hello")
        assert "|Hello|" in info.hex_preview or "Hello" in info.hex_preview

    def test_hex_dump_dots_for_non_printable(self):
        info = self.fa.analyze(b"\x00\x01\x02\x03")
        assert "." in info.hex_preview

    def test_hex_dump_empty_data(self):
        info = self.fa.analyze(b"")
        assert info.hex_preview == ""


# ---------------------------------------------------------------------------
# FileAnalyzer — FileInfo properties
# ---------------------------------------------------------------------------

class TestFileInfo:
    def test_success_true_when_no_error(self):
        info = FileInfo(path="", size=0, mime="text/plain", description="text", entropy=0.0)
        assert info.success is True

    def test_success_false_when_error(self):
        info = FileInfo(path="", size=0, mime="unknown", description="unknown", entropy=0.0, error="oops")
        assert info.success is False

    def test_error_from_missing_path(self, tmp_path):
        fa = FileAnalyzer()
        info = fa.analyze(tmp_path / "nonexistent.bin")
        assert not info.success
        assert info.error is not None


# ---------------------------------------------------------------------------
# StegDetector — PNG
# ---------------------------------------------------------------------------

class TestStegDetectorPNG:
    def setup_method(self):
        self.sd = StegDetector()

    def test_clean_png_low_score(self):
        data = make_png()
        result = self.sd.detect(data, "test.png")
        assert result.success
        assert result.score < 50

    def test_png_with_appended_data_detected(self):
        data = make_png(extra_after_iend=b"X" * 50)
        result = self.sd.detect(data, "test.png")
        assert result.appended_bytes == 50
        assert result.score > 0
        assert any("appended" in ind.lower() for ind in result.indicators)

    def test_png_unknown_chunk_raises_score(self):
        # Build PNG with a custom private chunk before IEND
        sig = b"\x89PNG\r\n\x1a\n"
        # Minimal IHDR
        ihdr_data = struct.pack(">IIBBBBB", 4, 4, 8, 0, 0, 0, 0)
        ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
        ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
        # Pixel data
        raw_rows = bytes([0] + [128] * 4) * 4
        compressed = zlib.compress(raw_rows)
        idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
        idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)
        # Unknown private chunk "tEsT"
        unknown_data = b"hidden data here"
        unk_crc = zlib.crc32(b"tEsT" + unknown_data) & 0xFFFFFFFF
        unknown_chunk = struct.pack(">I", len(unknown_data)) + b"tEsT" + unknown_data + struct.pack(">I", unk_crc)
        # IEND
        iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
        iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
        data = sig + ihdr + idat + unknown_chunk + iend
        result = self.sd.detect(data, "suspicious.png")
        assert result.score > 0

    def test_png_verdict_low(self):
        data = make_png()
        result = self.sd.detect(data, "clean.png")
        assert "LOW" in result.verdict

    def test_png_with_large_appended_verdict_high_or_medium(self):
        data = make_png(extra_after_iend=b"A" * 200)
        result = self.sd.detect(data, "suspicious.png")
        assert result.score >= 35


# ---------------------------------------------------------------------------
# StegDetector — BMP
# ---------------------------------------------------------------------------

class TestStegDetectorBMP:
    def setup_method(self):
        self.sd = StegDetector()

    def test_clean_bmp_low_score(self):
        data = make_bmp()
        result = self.sd.detect(data, "test.bmp")
        assert result.success
        assert result.score < 60

    def test_bmp_size_mismatch_detected(self):
        data = bytearray(make_bmp())
        # Corrupt declared file size to mismatch actual
        struct.pack_into("<I", data, 2, len(data) + 100)
        result = self.sd.detect(bytes(data), "corrupt.bmp")
        assert any("size" in ind.lower() or "size" in ind for ind in result.indicators)
        assert result.score > 0


# ---------------------------------------------------------------------------
# StegDetector — JPEG
# ---------------------------------------------------------------------------

class TestStegDetectorJPEG:
    def setup_method(self):
        self.sd = StegDetector()

    def test_clean_jpeg_low_score(self):
        data = make_jpeg_minimal()
        result = self.sd.detect(data, "test.jpg")
        assert result.success
        assert result.score < 40

    def test_jpeg_with_appended_data_detected(self):
        appended = b"secret data here" * 5
        data = make_jpeg_minimal(appended=appended)
        result = self.sd.detect(data, "test.jpg")
        assert result.appended_bytes == len(appended)
        assert result.score > 0
        assert any("appended" in ind.lower() or "EOI" in ind for ind in result.indicators)

    def test_jpeg_appended_verdict_medium_or_high(self):
        data = make_jpeg_minimal(appended=b"X" * 100)
        result = self.sd.detect(data, "test.jpg")
        assert result.score >= 35


# ---------------------------------------------------------------------------
# StegDetector — unsupported format
# ---------------------------------------------------------------------------

class TestStegDetectorUnsupported:
    def setup_method(self):
        self.sd = StegDetector()

    def test_unsupported_format_zero_score(self):
        data = b"Hello, I am text"
        result = self.sd.detect(data, "file.txt")
        assert result.success
        assert result.score == 0

    def test_empty_data_no_crash(self):
        result = self.sd.detect(b"", "empty.png")
        # Should not raise; result may indicate error or low score
        assert isinstance(result, StegResult)
