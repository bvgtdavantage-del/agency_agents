import logging
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class DNSRecord:
    record_type: str
    value: str


@dataclass
class DNSResult:
    domain: str
    records: list[DNSRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    def by_type(self, rtype: str) -> list[DNSRecord]:
        return [r for r in self.records if r.record_type == rtype]


class DNSEnumerator:
    DIG_RECORD_TYPES = ["MX", "NS", "TXT"]
    RECORD_TYPES = ["A", "AAAA"] + DIG_RECORD_TYPES

    DIG_MISSING_WARNING = (
        "dig not found: {types} records were not queried. "
        "Install it with `sudo apt install dnsutils` or `brew install bind`."
    )

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

    def _resolve_via_dig(self, domain: str, record_type: str) -> list[DNSRecord]:
        try:
            completed = subprocess.run(
                ["dig", "+short", record_type, domain],
                capture_output=True, text=True, timeout=self.config.timeout
            )
        except Exception:
            return []
        records = []
        for line in completed.stdout.strip().splitlines():
            line = line.strip().strip('"')
            if line:
                records.append(DNSRecord(record_type, line))
        return records

    def enumerate(self, domain: str) -> DNSResult:
        result = DNSResult(domain=domain)
        try:
            result.records.extend(self._resolve_a(domain))
            result.records.extend(self._resolve_aaaa(domain))

            if shutil.which("dig"):
                for record_type in self.DIG_RECORD_TYPES:
                    result.records.extend(self._resolve_via_dig(domain, record_type))
            else:
                warning = self.DIG_MISSING_WARNING.format(
                    types=", ".join(self.DIG_RECORD_TYPES)
                )
                result.warnings.append(warning)
                logger.warning(warning)
        except Exception as exc:
            result.error = str(exc)
        return result

    def reverse_lookup(self, ip: str) -> Optional[str]:
        try:
            return socket.gethostbyaddr(ip)[0]
        except socket.herror:
            return None
