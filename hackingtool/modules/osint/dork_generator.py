from dataclasses import dataclass, field
from typing import List


@dataclass
class DorkQuery:
    category: str
    description: str
    query: str


@dataclass
class DorkResult:
    target: str
    queries: List[DorkQuery] = field(default_factory=list)

    def by_category(self, category: str) -> List[DorkQuery]:
        return [q for q in self.queries if q.category == category]

    def all_queries(self) -> List[str]:
        return [q.query for q in self.queries]


# Category identifiers used throughout this module
_EXPOSED_FILES = "exposed_files"
_LOGIN_PAGES = "login_pages"
_TECH_STACK = "tech_stack"
_SUBDOMAINS = "subdomains"
_SENSITIVE_DIRS = "sensitive_dirs"
_EMAILS = "emails"
_CODE_REPOS = "code_repos"

ALL_CATEGORIES = (
    _EXPOSED_FILES,
    _LOGIN_PAGES,
    _TECH_STACK,
    _SUBDOMAINS,
    _SENSITIVE_DIRS,
    _EMAILS,
    _CODE_REPOS,
)


def _exposed_files(target: str) -> List[DorkQuery]:
    filetypes = [
        ("pdf", "PDF documents"),
        ("xlsx", "Excel spreadsheets"),
        ("doc", "Word documents"),
        ("sql", "SQL database dumps"),
        ("log", "Log files"),
        ("env", "Environment configuration files"),
        ("bak", "Backup files"),
    ]
    return [
        DorkQuery(
            category=_EXPOSED_FILES,
            description=f"Publicly indexed {desc} on {target}",
            query=f"site:{target} filetype:{ext}",
        )
        for ext, desc in filetypes
    ]


def _login_pages(target: str) -> List[DorkQuery]:
    paths = [
        ("login", "Login pages"),
        ("admin", "Admin panels"),
        ("signin", "Sign-in pages"),
        ("portal", "Portal pages"),
        ("dashboard", "Dashboard pages"),
    ]
    return [
        DorkQuery(
            category=_LOGIN_PAGES,
            description=f"{desc} on {target}",
            query=f"site:{target} inurl:{path}",
        )
        for path, desc in paths
    ]


def _tech_stack(target: str) -> List[DorkQuery]:
    entries = [
        ('intext:"powered by"', "CMS / framework disclosure"),
        ('intext:"index of"', "Directory listing pages"),
        ('intitle:"phpMyAdmin"', "Exposed phpMyAdmin instances"),
        ("inurl:wp-admin", "WordPress admin interfaces"),
        ("inurl:joomla", "Joomla CMS instances"),
    ]
    return [
        DorkQuery(
            category=_TECH_STACK,
            description=f"{desc} on {target}",
            query=f"site:{target} {operator}",
        )
        for operator, desc in entries
    ]


def _subdomains(target: str) -> List[DorkQuery]:
    return [
        DorkQuery(
            category=_SUBDOMAINS,
            description=f"All indexed subdomains of {target}",
            query=f"site:*.{target}",
        ),
        DorkQuery(
            category=_SUBDOMAINS,
            description=f"Pages referencing {target} excluding www",
            query=f"inurl:{target} -site:www.{target}",
        ),
    ]


def _sensitive_dirs(target: str) -> List[DorkQuery]:
    entries = [
        ('intitle:"index of" /', "Open directory listings"),
        ("inurl:backup", "Backup directories"),
        ("inurl:config", "Configuration directories"),
        ("inurl:test", "Test or staging directories"),
        ("inurl:.git", "Exposed .git repositories"),
    ]
    return [
        DorkQuery(
            category=_SENSITIVE_DIRS,
            description=f"{desc} on {target}",
            query=f"site:{target} {operator}",
        )
        for operator, desc in entries
    ]


def _emails(target: str) -> List[DorkQuery]:
    return [
        DorkQuery(
            category=_EMAILS,
            description=f"Email addresses at {target} domain",
            query=f'"@{target}" email',
        ),
        DorkQuery(
            category=_EMAILS,
            description=f"Contact pages with email addresses on {target}",
            query=f'site:{target} "contact" email',
        ),
    ]


def _code_repos(target: str) -> List[DorkQuery]:
    sites = [
        ("github.com", "GitHub"),
        ("gitlab.com", "GitLab"),
        ("pastebin.com", "Pastebin"),
    ]
    return [
        DorkQuery(
            category=_CODE_REPOS,
            description=f"Code or pastes referencing {target} on {site_label}",
            query=f"site:{site_domain} {target}",
        )
        for site_domain, site_label in sites
    ]


class DorkGenerator:
    """Generates Google dork queries for passive OSINT reconnaissance.

    No network calls are made; this is pure query construction logic.
    """

    def generate(self, target: str) -> DorkResult:
        """Return a DorkResult containing all dork queries for *target* (a domain)."""
        builders = [
            _exposed_files,
            _login_pages,
            _tech_stack,
            _subdomains,
            _sensitive_dirs,
            _emails,
            _code_repos,
        ]
        queries: List[DorkQuery] = []
        for builder in builders:
            queries.extend(builder(target))

        return DorkResult(target=target, queries=queries)
