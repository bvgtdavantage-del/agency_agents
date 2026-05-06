import socket
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config


@dataclass
class DNSRecord:
    record_type: str
    value: str


@dataclass
class DNSResult:
    domain: str
    records: list[DNSRecord] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def by_type(self, rtype: str) -> list[DNSRecord]:
        return [r for r in self.records if r.record_type == rtype]


class DNSEnumerator:
    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"]

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _resolve_a(self, domain: str) -> list[DNSRecord]:
        try:
            addrs = socket.getaddrinfo(domain, None, socket.AF_INET)
            seen = set()
            records = []
            for addr in addrs:
                ip = addr[4][0]
                if ip not in seen:
                    seen.add(ip)
                    records.append(DNSRecord("A", ip))
            return records
        except socket.gaierror:
            return []

    def _resolve_aaaa(self, domain: str) -> list[DNSRecord]:
        try:
            addrs = socket.getaddrinfo(domain, None, socket.AF_INET6)
            seen = set()
            records = []
            for addr in addrs:
                ip = addr[4][0]
                if ip not in seen:
                    seen.add(ip)
                    records.append(DNSRecord("AAAA", ip))
            return records
        except socket.gaierror:
            return []

    def _resolve_mx(self, domain: str) -> list[DNSRecord]:
        try:
            import subprocess
            result = subprocess.run(
                ["dig", "+short", "MX", domain],
                capture_output=True, text=True, timeout=self.config.timeout
            )
            records = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    records.append(DNSRecord("MX", line))
            return records
        except Exception:
            return []

    def _resolve_ns(self, domain: str) -> list[DNSRecord]:
        try:
            import subprocess
            result = subprocess.run(
                ["dig", "+short", "NS", domain],
                capture_output=True, text=True, timeout=self.config.timeout
            )
            records = []
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if line:
                    records.append(DNSRecord("NS", line))
            return records
        except Exception:
            return []

    def _resolve_txt(self, domain: str) -> list[DNSRecord]:
        try:
            import subprocess
            result = subprocess.run(
                ["dig", "+short", "TXT", domain],
                capture_output=True, text=True, timeout=self.config.timeout
            )
            records = []
            for line in result.stdout.strip().splitlines():
                line = line.strip().strip('"')
                if line:
                    records.append(DNSRecord("TXT", line))
            return records
        except Exception:
            return []

    def enumerate(self, domain: str) -> DNSResult:
        result = DNSResult(domain=domain)
        try:
            result.records.extend(self._resolve_a(domain))
            result.records.extend(self._resolve_aaaa(domain))
            result.records.extend(self._resolve_mx(domain))
            result.records.extend(self._resolve_ns(domain))
            result.records.extend(self._resolve_txt(domain))
        except Exception as exc:
            result.error = str(exc)
        return result

    def reverse_lookup(self, ip: str) -> Optional[str]:
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.herror:
            return None
