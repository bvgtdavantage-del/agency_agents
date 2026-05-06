import ssl
import socket
import datetime
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config


@dataclass
class SSLReport:
    host: str
    port: int
    subject: dict[str, str] = field(default_factory=dict)
    issuer: dict[str, str] = field(default_factory=dict)
    version: Optional[str] = None
    cipher: Optional[tuple] = None
    not_before: Optional[datetime.datetime] = None
    not_after: Optional[datetime.datetime] = None
    san: list[str] = field(default_factory=list)
    days_remaining: Optional[int] = None
    expired: bool = False
    self_signed: bool = False
    weak_cipher: bool = False
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def grade(self) -> str:
        if self.error or self.expired:
            return "F"
        if self.self_signed or self.weak_cipher:
            return "C"
        if self.days_remaining and self.days_remaining < 30:
            return "B"
        return "A"


WEAK_CIPHERS = {
    "RC4", "DES", "3DES", "NULL", "EXPORT", "ADH", "AECDH", "aNULL", "eNULL"
}


class SSLChecker:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _parse_dn(self, dn_tuple: tuple) -> dict[str, str]:
        result = {}
        for entry in dn_tuple:
            for key, value in entry:
                result[key] = value
        return result

    def _is_weak_cipher(self, cipher_name: str) -> bool:
        upper = cipher_name.upper()
        return any(w in upper for w in WEAK_CIPHERS)

    def check(self, host: str, port: int = 443) -> SSLReport:
        report = SSLReport(host=host, port=port)
        ctx = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=self.config.timeout) as raw_sock:
                with ctx.wrap_socket(raw_sock, server_hostname=host) as ssl_sock:
                    cert = ssl_sock.getpeercert()
                    report.version = ssl_sock.version()
                    report.cipher = ssl_sock.cipher()

                    report.subject = self._parse_dn(cert.get("subject", ()))
                    report.issuer = self._parse_dn(cert.get("issuer", ()))

                    not_before_str = cert.get("notBefore", "")
                    not_after_str = cert.get("notAfter", "")
                    fmt = "%b %d %H:%M:%S %Y %Z"
                    if not_before_str:
                        report.not_before = datetime.datetime.strptime(not_before_str, fmt)
                    if not_after_str:
                        report.not_after = datetime.datetime.strptime(not_after_str, fmt)
                        now = datetime.datetime.utcnow()
                        report.expired = report.not_after < now
                        report.days_remaining = (report.not_after - now).days

                    san_entries = cert.get("subjectAltName", [])
                    report.san = [v for _, v in san_entries]

                    if report.subject.get("commonName") == report.issuer.get("commonName"):
                        report.self_signed = True

                    if report.cipher:
                        report.weak_cipher = self._is_weak_cipher(report.cipher[0])

        except ssl.SSLCertVerificationError as exc:
            report.error = f"Certificate verification failed: {exc}"
        except ssl.SSLError as exc:
            report.error = f"SSL error: {exc}"
        except Exception as exc:
            report.error = str(exc)

        return report
