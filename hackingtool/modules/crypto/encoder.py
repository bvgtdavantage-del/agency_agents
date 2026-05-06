import base64
import binascii
import urllib.parse
import html
from typing import Union


class Encoder:
    """Encode and decode data in common security-relevant formats."""

    # --- Base64 ---

    def base64_encode(self, data: Union[str, bytes]) -> str:
        raw = data.encode() if isinstance(data, str) else data
        return base64.b64encode(raw).decode()

    def base64_decode(self, data: str) -> bytes:
        return base64.b64decode(data + "==")

    def base64_url_encode(self, data: Union[str, bytes]) -> str:
        raw = data.encode() if isinstance(data, str) else data
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    def base64_url_decode(self, data: str) -> bytes:
        padded = data + "=" * (4 - len(data) % 4)
        return base64.urlsafe_b64decode(padded)

    # --- Hex ---

    def hex_encode(self, data: Union[str, bytes]) -> str:
        raw = data.encode() if isinstance(data, str) else data
        return raw.hex()

    def hex_decode(self, data: str) -> bytes:
        return bytes.fromhex(data.replace(" ", "").replace("\\x", ""))

    # --- URL ---

    def url_encode(self, data: str, safe: str = "") -> str:
        return urllib.parse.quote(data, safe=safe)

    def url_decode(self, data: str) -> str:
        return urllib.parse.unquote(data)

    def url_encode_full(self, data: str) -> str:
        """Percent-encode every character including unreserved ones."""
        return "".join(f"%{b:02X}" for b in data.encode())

    # --- HTML ---

    def html_encode(self, data: str) -> str:
        return html.escape(data, quote=True)

    def html_decode(self, data: str) -> str:
        return html.unescape(data)

    # --- Binary ---

    def to_binary(self, data: str) -> str:
        return " ".join(f"{ord(c):08b}" for c in data)

    def from_binary(self, data: str) -> str:
        bits = data.replace(" ", "")
        chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
        return "".join(chr(int(c, 2)) for c in chars)

    # --- Octal ---

    def to_octal(self, data: str) -> str:
        return " ".join(f"{ord(c):o}" for c in data)

    def from_octal(self, data: str) -> str:
        return "".join(chr(int(o, 8)) for o in data.split())

    # --- ROT13 ---

    def rot13(self, data: str) -> str:
        result = []
        for c in data:
            if "a" <= c <= "z":
                result.append(chr((ord(c) - ord("a") + 13) % 26 + ord("a")))
            elif "A" <= c <= "Z":
                result.append(chr((ord(c) - ord("A") + 13) % 26 + ord("A")))
            else:
                result.append(c)
        return "".join(result)

    # --- Auto-detect and decode ---

    def smart_decode(self, data: str) -> dict[str, str]:
        """Attempt multiple decoding methods and return successful results."""
        results = {}

        try:
            decoded = self.base64_decode(data)
            results["base64"] = decoded.decode(errors="replace")
        except Exception:
            pass

        try:
            results["url"] = self.url_decode(data)
        except Exception:
            pass

        try:
            decoded = self.hex_decode(data)
            results["hex"] = decoded.decode(errors="replace")
        except Exception:
            pass

        results["rot13"] = self.rot13(data)

        try:
            results["html"] = self.html_decode(data)
        except Exception:
            pass

        return {k: v for k, v in results.items() if v and v != data}
