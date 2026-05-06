import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PatternMatch:
    pattern_name: str
    value: str
    start: int
    end: int


CTF_PATTERNS = {
    "flag_generic": r"(?i)(flag\{[^}]+\}|ctf\{[^}]+\}|htb\{[^}]+\}|thm\{[^}]+\}|picoctf\{[^}]+\})",
    "base64": r"[A-Za-z0-9+/]{20,}={0,2}",
    "hex_string": r"\b[0-9a-fA-F]{8,}\b",
    "url": r"https?://[^\s\"'<>]+",
    "ipv4": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "jwt": r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.+/]+",
    "md5": r"\b[a-f0-9]{32}\b",
    "sha256": r"\b[a-f0-9]{64}\b",
    "private_key": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    "aws_key": r"AKIA[0-9A-Z]{16}",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
}


class PatternSearch:
    def __init__(self, custom_patterns: Optional[dict[str, str]] = None):
        self.patterns = {**CTF_PATTERNS, **(custom_patterns or {})}

    def search(self, text: str, pattern_names: Optional[list[str]] = None) -> list[PatternMatch]:
        active = pattern_names or list(self.patterns.keys())
        matches = []
        for name in active:
            if name not in self.patterns:
                continue
            for m in re.finditer(self.patterns[name], text):
                matches.append(PatternMatch(name, m.group(), m.start(), m.end()))
        matches.sort(key=lambda m: m.start)
        return matches

    def search_file(self, path: str, pattern_names: Optional[list[str]] = None) -> list[PatternMatch]:
        with open(path, "r", errors="replace") as f:
            content = f.read()
        return self.search(content, pattern_names)

    def extract_flags(self, text: str) -> list[str]:
        return [m.value for m in self.search(text, ["flag_generic"])]

    def find_hidden_text(self, text: str) -> dict[str, list[str]]:
        results: dict[str, list[str]] = {}
        for name in self.patterns:
            found = [m.value for m in self.search(text, [name])]
            if found:
                results[name] = found
        return results
