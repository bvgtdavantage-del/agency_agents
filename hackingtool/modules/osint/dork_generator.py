"""Google dork query generator for OSINT reconnaissance."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Category → list of dork templates (%s = domain)
_DORKS: dict[str, list[tuple[str, str]]] = {
    "general": [
        ('site:{d}',                                    "All indexed pages"),
        ('site:{d} -www',                               "Non-www subdomains"),
        ('site:{d} intitle:"index of"',                 "Open directory listings"),
        ('site:{d} inurl:admin',                        "Admin panels"),
        ('site:{d} inurl:login',                        "Login pages"),
        ('site:{d} inurl:dashboard',                    "Dashboards"),
        ('site:{d} inurl:portal',                       "Portals"),
        ('related:{d}',                                 "Related/similar sites"),
        ('link:{d}',                                    "Sites linking to target"),
        ('"@{d}"',                                      "Email addresses"),
    ],
    "exposed_files": [
        ('site:{d} ext:pdf',                            "Exposed PDF files"),
        ('site:{d} ext:xls OR ext:xlsx',                "Exposed spreadsheets"),
        ('site:{d} ext:doc OR ext:docx',                "Exposed Word documents"),
        ('site:{d} ext:sql',                            "Exposed SQL files"),
        ('site:{d} ext:log',                            "Exposed log files"),
        ('site:{d} ext:bak OR ext:old OR ext:backup',   "Backup files"),
        ('site:{d} ext:env OR ext:cfg OR ext:conf',     "Config/env files"),
        ('site:{d} ext:xml inurl:sitemap',              "Sitemap files"),
        ('site:{d} filetype:json',                      "Exposed JSON files"),
        ('site:{d} intitle:"index of" "parent directory"', "Directory listings"),
    ],
    "login_pages": [
        ('site:{d} inurl:login',                        "Login pages"),
        ('site:{d} inurl:signin',                       "Sign-in pages"),
        ('site:{d} inurl:admin',                        "Admin panels"),
        ('site:{d} inurl:wp-admin',                     "WordPress admin"),
        ('site:{d} inurl:wp-login.php',                 "WordPress login"),
        ('site:{d} inurl:administrator',                "Administrator panels"),
        ('site:{d} inurl:phpmyadmin',                   "phpMyAdmin"),
        ('site:{d} inurl:cpanel',                       "cPanel"),
        ('site:{d} inurl:webmail',                      "Webmail"),
        ('site:{d} inurl:remote',                       "Remote access panels"),
    ],
    "subdomains": [
        ('site:*.{d} -www',                             "All subdomains (minus www)"),
        ('site:*.{d} inurl:dev',                        "Dev subdomains"),
        ('site:*.{d} inurl:staging',                    "Staging subdomains"),
        ('site:*.{d} inurl:test',                       "Test subdomains"),
        ('site:*.{d} inurl:api',                        "API subdomains"),
        ('site:*.{d} inurl:mail',                       "Mail subdomains"),
        ('site:*.{d} inurl:vpn',                        "VPN subdomains"),
        ('site:*.{d} inurl:remote',                     "Remote subdomains"),
        ('site:*.{d} inurl:beta',                       "Beta subdomains"),
        ('site:*.{d} inurl:internal',                   "Internal subdomains"),
    ],
    "sensitive_data": [
        ('site:{d} "password" OR "passwd" OR "pwd"',    "Password references"),
        ('site:{d} "api_key" OR "apikey" OR "api key"', "API key references"),
        ('site:{d} "secret" OR "token"',                "Secret/token references"),
        ('site:{d} "username" "password" filetype:log', "Credential logs"),
        ('site:{d} intext:"sql syntax near"',           "SQL error messages"),
        ('site:{d} intext:"Warning: mysql_"',           "MySQL errors"),
        ('site:{d} intext:"stack trace"',               "Stack traces"),
        ('site:{d} "BEGIN RSA PRIVATE KEY"',            "Exposed private keys"),
        ('site:{d} "AWS_SECRET_ACCESS_KEY"',            "AWS keys"),
        ('site:{d} inurl:".git" intitle:"Index of"',    "Exposed .git directory"),
    ],
    "technology": [
        ('site:{d} inurl:wp-content',                   "WordPress content"),
        ('site:{d} inurl:joomla',                       "Joomla CMS"),
        ('site:{d} inurl:drupal',                       "Drupal CMS"),
        ('site:{d} inurl:laravel',                      "Laravel framework"),
        ('site:{d} inurl:django',                       "Django framework"),
        ('site:{d} intitle:"IIS Windows Server"',       "IIS server"),
        ('site:{d} intitle:"Apache2 Ubuntu Default"',   "Apache default page"),
        ('site:{d} inurl:jenkins',                      "Jenkins CI"),
        ('site:{d} inurl:grafana',                      "Grafana dashboard"),
        ('site:{d} inurl:kibana',                       "Kibana dashboard"),
    ],
}

CATEGORIES = list(_DORKS.keys())


@dataclass
class Dork:
    query: str
    description: str
    search_url: str


@dataclass
class DorkResult:
    domain: str
    category: str
    dorks: List[Dork] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class DorkGenerator:
    """Generate Google dork queries for passive OSINT reconnaissance."""

    _BASE = "https://www.google.com/search?q={}"

    def generate(self, domain: str, category: str = "general") -> DorkResult:
        domain = domain.strip().lstrip("https://").lstrip("http://").rstrip("/")
        if category not in _DORKS and category != "all":
            return DorkResult(domain=domain, category=category,
                              error=f"Unknown category '{category}'. Choose: {', '.join(CATEGORIES + ['all'])}")

        categories = list(_DORKS.keys()) if category == "all" else [category]
        dorks: list[Dork] = []
        for cat in categories:
            for tmpl, desc in _DORKS[cat]:
                query = tmpl.format(d=domain)
                url = self._BASE.format(urllib.parse.quote_plus(query))
                dorks.append(Dork(query=query, description=desc, search_url=url))

        return DorkResult(domain=domain, category=category, dorks=dorks)
