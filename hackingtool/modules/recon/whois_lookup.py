import socket
import re
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config


@dataclass
class WhoisResult:
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    name_servers: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    raw: str = ""
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class WhoisLookup:
    WHOIS_PORT = 43
    WHOIS_SERVER = "whois.iana.org"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _query(self, server: str, domain: str) -> str:
        with socket.create_connection((server, self.WHOIS_PORT), timeout=self.config.timeout) as sock:
            sock.sendall(f"{domain}\r\n".encode())
            chunks = []
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return b"".join(chunks).decode(errors="replace")

    def _find_referred_server(self, raw: str) -> Optional[str]:
        for line in raw.splitlines():
            lower = line.lower()
            if lower.startswith("refer:") or lower.startswith("whois:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None

    def _extract_field(self, raw: str, *keys: str) -> Optional[str]:
        for line in raw.splitlines():
            for key in keys:
                if line.lower().startswith(key.lower() + ":"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        return value
        return None

    def _extract_list_field(self, raw: str, *keys: str) -> list[str]:
        results = []
        for line in raw.splitlines():
            for key in keys:
                if line.lower().startswith(key.lower() + ":"):
                    value = line.split(":", 1)[1].strip()
                    if value:
                        results.append(value)
        return results

    def lookup(self, domain: str) -> WhoisResult:
        result = WhoisResult(domain=domain)
        try:
            raw = self._query(self.WHOIS_SERVER, domain)
            referred = self._find_referred_server(raw)
            if referred:
                raw = self._query(referred, domain)
            result.raw = raw
            result.registrar = self._extract_field(raw, "Registrar", "registrar")
            result.creation_date = self._extract_field(raw, "Creation Date", "created", "Created Date")
            result.expiration_date = self._extract_field(raw, "Registry Expiry Date", "Expiry Date", "Expiration Date")
            result.name_servers = self._extract_list_field(raw, "Name Server")
            result.status = self._extract_list_field(raw, "Domain Status", "Status")
        except Exception as exc:
            result.error = str(exc)
        return result
