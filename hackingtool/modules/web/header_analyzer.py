import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config


SECURITY_HEADERS = {
    "Strict-Transport-Security": "Enforces HTTPS connections",
    "Content-Security-Policy": "Prevents XSS and injection attacks",
    "X-Frame-Options": "Prevents clickjacking",
    "X-Content-Type-Options": "Prevents MIME-type sniffing",
    "Referrer-Policy": "Controls referrer information",
    "Permissions-Policy": "Controls browser feature access",
    "X-XSS-Protection": "Legacy XSS filter (deprecated but common)",
    "Cache-Control": "Controls caching behavior",
    "Access-Control-Allow-Origin": "CORS policy header",
}

RISK_HEADERS = {
    "Server": "Discloses server software version",
    "X-Powered-By": "Discloses backend technology",
    "X-AspNet-Version": "Discloses ASP.NET version",
    "X-AspNetMvc-Version": "Discloses ASP.NET MVC version",
}


@dataclass
class HeaderFinding:
    header: str
    present: bool
    value: Optional[str]
    description: str
    severity: str


@dataclass
class HeaderReport:
    url: str
    status_code: Optional[int]
    all_headers: dict[str, str]
    security_findings: list[HeaderFinding] = field(default_factory=list)
    risk_findings: list[HeaderFinding] = field(default_factory=list)
    score: int = 0
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def grade(self) -> str:
        if self.score >= 90:
            return "A+"
        if self.score >= 80:
            return "A"
        if self.score >= 70:
            return "B"
        if self.score >= 60:
            return "C"
        if self.score >= 50:
            return "D"
        return "F"


class HeaderAnalyzer:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _fetch_headers(self, url: str) -> tuple[int, dict[str, str]]:
        req = urllib.request.Request(url, headers={"User-Agent": self.config.user_agent})
        with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
            return resp.status, dict(resp.headers)

    def analyze(self, url: str) -> HeaderReport:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        report = HeaderReport(url=url, status_code=None, all_headers={})
        try:
            status, headers = self._fetch_headers(url)
            report.status_code = status
            report.all_headers = {k.lower(): v for k, v in headers.items()}

            points = 0
            per_header = 100 // len(SECURITY_HEADERS)

            for name, desc in SECURITY_HEADERS.items():
                present = name.lower() in report.all_headers
                value = report.all_headers.get(name.lower()) if present else None
                severity = "info" if present else "medium"
                report.security_findings.append(
                    HeaderFinding(name, present, value, desc, severity)
                )
                if present:
                    points += per_header

            for name, desc in RISK_HEADERS.items():
                present = name.lower() in report.all_headers
                value = report.all_headers.get(name.lower()) if present else None
                severity = "low" if not present else "medium"
                report.risk_findings.append(
                    HeaderFinding(name, present, value, desc, severity)
                )
                if present:
                    points = max(0, points - 5)

            report.score = min(100, points)
        except urllib.error.HTTPError as exc:
            report.status_code = exc.code
            report.all_headers = dict(exc.headers)
            report.error = f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:
            report.error = str(exc)

        return report
