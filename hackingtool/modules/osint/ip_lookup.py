import urllib.request
import urllib.error
import json
import socket
from dataclasses import dataclass
from typing import Optional
from hackingtool.core.config import Config


@dataclass
class IPInfo:
    ip: str
    hostname: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    org: Optional[str] = None
    isp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    is_bogon: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def coordinates(self) -> Optional[str]:
        if self.latitude and self.longitude:
            return f"{self.latitude},{self.longitude}"
        return None


BOGON_RANGES = [
    ("0.0.0.0", "0.255.255.255"),
    ("10.0.0.0", "10.255.255.255"),
    ("100.64.0.0", "100.127.255.255"),
    ("127.0.0.0", "127.255.255.255"),
    ("169.254.0.0", "169.254.255.255"),
    ("172.16.0.0", "172.31.255.255"),
    ("192.0.0.0", "192.0.0.255"),
    ("192.168.0.0", "192.168.255.255"),
    ("198.18.0.0", "198.19.255.255"),
    ("198.51.100.0", "198.51.100.255"),
    ("203.0.113.0", "203.0.113.255"),
    ("240.0.0.0", "255.255.255.255"),
]


def _ip_to_int(ip: str) -> int:
    parts = [int(p) for p in ip.split(".")]
    return (parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]


def _is_bogon(ip: str) -> bool:
    try:
        addr = _ip_to_int(ip)
        for start, end in BOGON_RANGES:
            if _ip_to_int(start) <= addr <= _ip_to_int(end):
                return True
    except Exception:
        pass
    return False


class IPLookup:
    # Uses ip-api.com (free, no key required, max 45 req/min)
    _API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query,reverse"

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _resolve(self, host: str) -> Optional[str]:
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            return None

    def lookup(self, host: str) -> IPInfo:
        ip = host if self._is_ip(host) else self._resolve(host)
        if not ip:
            return IPInfo(ip=host, error=f"Could not resolve hostname: {host}")

        info = IPInfo(ip=ip)
        info.is_bogon = _is_bogon(ip)

        if info.is_bogon:
            info.hostname = host if host != ip else None
            return info

        try:
            url = self._API_URL.format(ip=ip)
            req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent})
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode())

            if data.get("status") == "fail":
                info.error = data.get("message", "Lookup failed")
                return info

            info.hostname = data.get("reverse") or (host if host != ip else None)
            info.city = data.get("city")
            info.region = data.get("regionName")
            info.country = data.get("country")
            info.country_code = data.get("countryCode")
            info.org = data.get("org")
            info.isp = data.get("isp")
            info.latitude = data.get("lat")
            info.longitude = data.get("lon")
            info.timezone = data.get("timezone")

        except Exception as exc:
            info.error = str(exc)

        return info

    def my_ip(self) -> IPInfo:
        try:
            req = urllib.request.Request(
                "http://ip-api.com/json/?fields=query",
                headers={"User-Agent": self.config.user_agent}
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                data = json.loads(resp.read().decode())
            return self.lookup(data.get("query", ""))
        except Exception as exc:
            return IPInfo(ip="unknown", error=str(exc))

    @staticmethod
    def _is_ip(host: str) -> bool:
        try:
            socket.inet_aton(host)
            return True
        except socket.error:
            return False
