import urllib.request
import urllib.error
import json
from dataclasses import dataclass, field
from typing import List, Optional
from hackingtool.core.config import Config


@dataclass
class CertRecord:
    domain: str
    issuer: str
    not_before: str
    not_after: str
    serial: str


@dataclass
class CertResult:
    domain: str
    records: List[CertRecord] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class CertTransparency:
    _API_URL = "https://crt.sh/?q=%25.{domain}&output=json"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def lookup(self, domain: str) -> CertResult:
        result = CertResult(domain=domain)
        try:
            url = self._API_URL.format(domain=domain)
            req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent})
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode())

            for entry in data:
                result.records.append(CertRecord(
                    domain=entry.get("name_value", ""),
                    issuer=str(entry.get("issuer_name") or entry.get("issuer_ca_id", "")),
                    not_before=entry.get("not_before", ""),
                    not_after=entry.get("not_after", ""),
                    serial=entry.get("serial_number", ""),
                ))

            result.subdomains = self._extract_subdomains(result.records, domain)

        except Exception as exc:
            result.error = str(exc)

        return result

    def _extract_subdomains(self, records: List[CertRecord], base_domain: str) -> List[str]:
        seen = set()
        for record in records:
            # name_value can contain newline-separated SANs
            for name in record.domain.splitlines():
                name = name.strip().lower()
                # Wildcards like *.example.com → example.com
                if name.startswith("*."):
                    name = name[2:]
                if name and (name == base_domain or name.endswith("." + base_domain)):
                    seen.add(name)
        return sorted(seen)
