from typing import Optional


class CipherTools:
    """Classic cipher implementations for CTF challenges."""

    # --- Caesar Cipher ---

    def caesar_encrypt(self, text: str, shift: int) -> str:
        return self._caesar(text, shift)

    def caesar_decrypt(self, text: str, shift: int) -> str:
        return self._caesar(text, -shift)

    def caesar_brute(self, text: str) -> list[tuple[int, str]]:
        return [(shift, self._caesar(text, shift)) for shift in range(1, 26)]

    def _caesar(self, text: str, shift: int) -> str:
        result = []
        for c in text:
            if c.isalpha():
                base = ord("A") if c.isupper() else ord("a")
                result.append(chr((ord(c) - base + shift) % 26 + base))
            else:
                result.append(c)
        return "".join(result)

    # --- Vigenere Cipher ---

    def vigenere_encrypt(self, text: str, key: str) -> str:
        return self._vigenere(text, key, decrypt=False)

    def vigenere_decrypt(self, text: str, key: str) -> str:
        return self._vigenere(text, key, decrypt=True)

    def _vigenere(self, text: str, key: str, decrypt: bool) -> str:
        key = key.upper()
        result = []
        ki = 0
        for c in text:
            if c.isalpha():
                shift = ord(key[ki % len(key)]) - ord("A")
                if decrypt:
                    shift = -shift
                base = ord("A") if c.isupper() else ord("a")
                result.append(chr((ord(c) - base + shift) % 26 + base))
                ki += 1
            else:
                result.append(c)
        return "".join(result)

    # --- XOR ---

    def xor_single(self, data: bytes, key: int) -> bytes:
        return bytes(b ^ key for b in data)

    def xor_repeating(self, data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    def xor_brute_single(self, data: bytes) -> list[tuple[int, str]]:
        results = []
        for k in range(256):
            decoded = self.xor_single(data, k)
            try:
                text = decoded.decode("ascii")
                printable = sum(32 <= ord(c) < 127 for c in text)
                if printable / len(text) > 0.8:
                    results.append((k, text))
            except UnicodeDecodeError:
                pass
        return results

    # --- Atbash ---

    def atbash(self, text: str) -> str:
        result = []
        for c in text:
            if c.isalpha():
                base = ord("A") if c.isupper() else ord("a")
                result.append(chr(base + 25 - (ord(c) - base)))
            else:
                result.append(c)
        return "".join(result)

    # --- Morse Code ---

    MORSE = {
        "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".",
        "F": "..-.", "G": "--.", "H": "....", "I": "..", "J": ".---",
        "K": "-.-", "L": ".-..", "M": "--", "N": "-.", "O": "---",
        "P": ".--.", "Q": "--.-", "R": ".-.", "S": "...", "T": "-",
        "U": "..-", "V": "...-", "W": ".--", "X": "-..-", "Y": "-.--",
        "Z": "--..", "0": "-----", "1": ".----", "2": "..---",
        "3": "...--", "4": "....-", "5": ".....", "6": "-....",
        "7": "--...", "8": "---..", "9": "----.", " ": "/"
    }
    _MORSE_REV = {v: k for k, v in MORSE.items()}

    def morse_encode(self, text: str) -> str:
        return " ".join(self.MORSE.get(c.upper(), "?") for c in text)

    def morse_decode(self, code: str) -> str:
        return "".join(self._MORSE_REV.get(token, "?") for token in code.split(" "))

    # --- Rail Fence ---

    def rail_fence_encrypt(self, text: str, rails: int) -> str:
        fence = [[] for _ in range(rails)]
        rail, direction = 0, 1
        for c in text:
            fence[rail].append(c)
            if rail == 0:
                direction = 1
            elif rail == rails - 1:
                direction = -1
            rail += direction
        return "".join(c for row in fence for c in row)

    def rail_fence_decrypt(self, text: str, rails: int) -> str:
        n = len(text)
        pattern = []
        rail, direction = 0, 1
        for i in range(n):
            pattern.append(rail)
            if rail == 0:
                direction = 1
            elif rail == rails - 1:
                direction = -1
            rail += direction

        indices = sorted(range(n), key=lambda i: pattern[i])
        result = [""] * n
        for idx, char in zip(indices, text):
            result[idx] = char
        return "".join(result)
