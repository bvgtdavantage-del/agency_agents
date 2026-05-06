import pytest
from hackingtool.modules.ctf.cipher_tools import CipherTools
from hackingtool.modules.ctf.pattern_search import PatternSearch


class TestCipherTools:
    def setup_method(self):
        self.ct = CipherTools()

    # Caesar
    def test_caesar_encrypt_known(self):
        assert self.ct.caesar_encrypt("Hello", 3) == "Khoor"

    def test_caesar_decrypt_known(self):
        assert self.ct.caesar_decrypt("Khoor", 3) == "Hello"

    def test_caesar_encrypt_decrypt_roundtrip(self):
        plaintext = "The Quick Brown Fox"
        for shift in range(1, 26):
            enc = self.ct.caesar_encrypt(plaintext, shift)
            dec = self.ct.caesar_decrypt(enc, shift)
            assert dec == plaintext

    def test_caesar_preserves_non_alpha(self):
        assert self.ct.caesar_encrypt("Hello, World! 123", 13) == "Uryyb, Jbeyq! 123"

    def test_caesar_brute_returns_25_results(self):
        results = self.ct.caesar_brute("Khoor")
        assert len(results) == 25

    def test_caesar_brute_contains_correct_plaintext(self):
        results = self.ct.caesar_brute("Khoor")
        shifts = {shift: text for shift, text in results}
        assert shifts[23] == "Hello"

    # Vigenere
    def test_vigenere_encrypt_known(self):
        assert self.ct.vigenere_encrypt("ATTACKATDAWN", "LEMON") == "LXFOPVEFRNHR"

    def test_vigenere_decrypt_known(self):
        assert self.ct.vigenere_decrypt("LXFOPVEFRNHR", "LEMON") == "ATTACKATDAWN"

    def test_vigenere_roundtrip(self):
        plaintext = "HELLO WORLD"
        key = "SECRET"
        enc = self.ct.vigenere_encrypt(plaintext, key)
        dec = self.ct.vigenere_decrypt(enc, key)
        assert dec == plaintext

    # Atbash
    def test_atbash_known(self):
        assert self.ct.atbash("Hello") == "Svool"

    def test_atbash_double_is_identity(self):
        text = "HelloWorld"
        assert self.ct.atbash(self.ct.atbash(text)) == text

    # ROT13
    def test_rot13_via_caesar(self):
        assert self.ct.caesar_encrypt("Hello", 13) == "Uryyb"
        assert self.ct.caesar_encrypt("Uryyb", 13) == "Hello"

    # XOR
    def test_xor_single_known(self):
        result = self.ct.xor_single(b"Hello", 0x00)
        assert result == b"Hello"

    def test_xor_single_roundtrip(self):
        data = b"Secret data"
        key = 42
        assert self.ct.xor_single(self.ct.xor_single(data, key), key) == data

    def test_xor_repeating_known(self):
        data = b"Hello"
        key = b"\x00"
        assert self.ct.xor_repeating(data, key) == data

    def test_xor_repeating_roundtrip(self):
        data = b"The quick brown fox"
        key = b"KEY"
        enc = self.ct.xor_repeating(data, key)
        dec = self.ct.xor_repeating(enc, key)
        assert dec == data

    def test_xor_brute_single_finds_printable(self):
        message = b"Hello World"
        key = 0x55
        encrypted = self.ct.xor_single(message, key)
        results = self.ct.xor_brute_single(encrypted)
        keys = {k for k, _ in results}
        assert key in keys

    # Morse
    def test_morse_encode_known(self):
        assert self.ct.morse_encode("SOS") == "... --- ..."

    def test_morse_decode_known(self):
        assert self.ct.morse_decode("... --- ...") == "SOS"

    def test_morse_roundtrip(self):
        text = "HELLO WORLD"
        encoded = self.ct.morse_encode(text)
        decoded = self.ct.morse_decode(encoded)
        assert decoded == text

    # Rail Fence
    def test_rail_fence_encrypt_known(self):
        assert self.ct.rail_fence_encrypt("WEAREDISCOVEREDFLEEABNOW", 3) == "WECRLBERDSOEEFEANWAIVDEO"

    def test_rail_fence_decrypt_known(self):
        assert self.ct.rail_fence_decrypt("WECRLBERDSOEEFEANWAIVDEO", 3) == "WEAREDISCOVEREDFLEEABNOW"

    def test_rail_fence_roundtrip(self):
        text = "THEQUICKBROWNFOX"
        for rails in range(2, 6):
            enc = self.ct.rail_fence_encrypt(text, rails)
            dec = self.ct.rail_fence_decrypt(enc, rails)
            assert dec == text


class TestPatternSearch:
    def setup_method(self):
        self.ps = PatternSearch()

    def test_finds_flag_format(self):
        text = "Look here: flag{this_is_the_flag} did you find it?"
        matches = self.ps.extract_flags(text)
        assert len(matches) == 1
        assert "flag{this_is_the_flag}" in matches[0]

    def test_finds_htb_flag(self):
        text = "HTB{s0m3_fl4g_h3r3}"
        flags = self.ps.extract_flags(text)
        assert len(flags) == 1

    def test_finds_md5_pattern(self):
        text = "The hash is 5f4dcc3b5aa765d61d8327deb882cf99 in the output"
        matches = self.ps.search(text, ["md5"])
        assert len(matches) >= 1
        assert matches[0].value == "5f4dcc3b5aa765d61d8327deb882cf99"

    def test_finds_url_pattern(self):
        text = "Visit https://example.com for more info"
        matches = self.ps.search(text, ["url"])
        assert len(matches) >= 1

    def test_finds_ipv4(self):
        text = "Connect to 192.168.1.1 on port 80"
        matches = self.ps.search(text, ["ipv4"])
        assert any("192.168.1.1" in m.value for m in matches)

    def test_finds_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        matches = self.ps.search(jwt, ["jwt"])
        assert len(matches) >= 1

    def test_finds_email(self):
        text = "Contact admin@example.com for support"
        matches = self.ps.search(text, ["email"])
        assert any("admin@example.com" in m.value for m in matches)

    def test_find_hidden_text_returns_dict(self):
        text = "hash: 5f4dcc3b5aa765d61d8327deb882cf99"
        result = self.ps.find_hidden_text(text)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_no_match_returns_empty(self):
        matches = self.ps.search("nothing special here", ["flag_generic", "jwt"])
        assert matches == []

    def test_match_positions_are_correct(self):
        text = "prefix flag{test} suffix"
        matches = self.ps.search(text, ["flag_generic"])
        assert len(matches) == 1
        assert text[matches[0].start:matches[0].end] == matches[0].value
