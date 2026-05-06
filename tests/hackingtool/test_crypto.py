import pytest
from hackingtool.modules.crypto.hash_tools import HashIdentifier, HashGenerator
from hackingtool.modules.crypto.encoder import Encoder


class TestHashIdentifier:
    def setup_method(self):
        self.hi = HashIdentifier()

    def test_identifies_md5(self):
        matches = self.hi.identify("5f4dcc3b5aa765d61d8327deb882cf99")
        algos = [m.algorithm for m in matches]
        assert "MD5" in algos

    def test_identifies_sha1(self):
        matches = self.hi.identify("aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d")
        algos = [m.algorithm for m in matches]
        assert "SHA-1" in algos

    def test_identifies_sha256(self):
        h = "a" * 64
        matches = self.hi.identify(h)
        algos = [m.algorithm for m in matches]
        assert "SHA-256" in algos

    def test_identifies_sha512(self):
        h = "b" * 128
        matches = self.hi.identify(h)
        algos = [m.algorithm for m in matches]
        assert "SHA-512" in algos

    def test_identifies_bcrypt(self):
        h = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
        matches = self.hi.identify(h)
        algos = [m.algorithm for m in matches]
        assert "bcrypt" in algos

    def test_unknown_hash_returns_empty(self):
        matches = self.hi.identify("notahash")
        assert matches == []

    def test_is_known_hash_true(self):
        assert self.hi.is_known_hash("5f4dcc3b5aa765d61d8327deb882cf99") is True

    def test_is_known_hash_false(self):
        assert self.hi.is_known_hash("hello world") is False


class TestHashGenerator:
    def setup_method(self):
        self.gen = HashGenerator()

    def test_generate_sha256(self):
        result = self.gen.generate("hello", "sha256")
        assert result == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_generate_md5(self):
        result = self.gen.generate("hello", "md5")
        assert result == "5d41402abc4b2a76b9719d911017c592"

    def test_generate_sha1(self):
        result = self.gen.generate("hello", "sha1")
        assert result == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"

    def test_generate_unknown_algorithm_returns_none(self):
        assert self.gen.generate("hello", "nonexistent") is None

    def test_generate_all_returns_all_algorithms(self):
        results = self.gen.generate_all("test")
        assert "sha256" in results
        assert "md5" in results
        assert "sha512" in results
        assert len(results) == len(self.gen.supported_algorithms)

    def test_supported_algorithms_not_empty(self):
        assert len(self.gen.supported_algorithms) > 5


class TestEncoder:
    def setup_method(self):
        self.enc = Encoder()

    def test_base64_roundtrip(self):
        original = "Hello, World!"
        encoded = self.enc.base64_encode(original)
        decoded = self.enc.base64_decode(encoded).decode()
        assert decoded == original

    def test_base64_encode_known_value(self):
        assert self.enc.base64_encode("hello") == "aGVsbG8="

    def test_base64_url_roundtrip(self):
        original = "test+data/here="
        encoded = self.enc.base64_url_encode(original)
        decoded = self.enc.base64_url_decode(encoded).decode()
        assert decoded == original

    def test_hex_roundtrip(self):
        original = "deadbeef"
        encoded = self.enc.hex_encode(original)
        decoded = self.enc.hex_decode(encoded).decode()
        assert decoded == original

    def test_hex_encode_known_value(self):
        assert self.enc.hex_encode("hi") == "6869"

    def test_url_encode_decode(self):
        original = "hello world & more"
        encoded = self.enc.url_encode(original)
        assert " " not in encoded
        assert self.enc.url_decode(encoded) == original

    def test_html_encode_decode(self):
        original = '<script>alert("xss")</script>'
        encoded = self.enc.html_encode(original)
        assert "<script>" not in encoded
        assert self.enc.html_decode(encoded) == original

    def test_rot13_known_value(self):
        assert self.enc.rot13("Hello") == "Uryyb"

    def test_rot13_double_application_is_identity(self):
        text = "Secret Message 123"
        assert self.enc.rot13(self.enc.rot13(text)) == text

    def test_binary_roundtrip(self):
        original = "Hi"
        encoded = self.enc.to_binary(original)
        decoded = self.enc.from_binary(encoded)
        assert decoded == original

    def test_octal_roundtrip(self):
        original = "AB"
        encoded = self.enc.to_octal(original)
        decoded = self.enc.from_octal(encoded)
        assert decoded == original

    def test_smart_decode_finds_base64(self):
        b64 = self.enc.base64_encode("hidden secret")
        results = self.enc.smart_decode(b64)
        assert "base64" in results
        assert "hidden secret" in results["base64"]

    def test_smart_decode_returns_empty_for_plain_text(self):
        results = self.enc.smart_decode("plaintext")
        assert isinstance(results, dict)
