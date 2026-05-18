"""Certificate Transparency log lookup via crt.sh — passive subdomain discovery."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional
from hackingtool.core.config import Config


@dataclass
class CertResult:
    domain: str
    subdomains: List[str] = field(default_factory=list)
    total_certs: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class CertTransparency:
    """Query crt.sh certificate transparency logs for passive subdomain discovery."""

    _API = "https://crt.sh/?q=%25.{domain}&output=json"

    def __init__(self, cfg: Optional[Config] = None):
        self.timeout = cfg.timeout if cfg else 10

    def query(self, domain: str) -> CertResult:
        url = self._API.format(domain=domain.lstrip("*.").strip())
        req = urllib.request.Request(url, headers={"User-Agent": "hackingtool-osint/2.0"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            return CertResult(domain=domain, error=str(exc))
        except Exception as exc:
            return CertResult(domain=domain, error=str(exc))

        seen: set[str] = set()
        for entry in data:
            name_value = entry.get("name_value", "")
            for name in name_value.splitlines():
                name = name.strip().lstrip("*.")
                if name and domain in name:
                    seen.add(name.lower())

        subdomains = sorted(seen)
        return CertResult(domain=domain, subdomains=subdomains, total_certs=len(data))
