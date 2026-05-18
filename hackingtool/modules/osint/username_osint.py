"""Username OSINT — check presence across popular platforms via passive HTTP probing."""

from __future__ import annotations

import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional
from hackingtool.core.config import Config


# Platform registry: (name, url_template, expected_status, false_positive_string)
# false_positive_string: if this string appears in the body, it's a 404-in-disguise
_PLATFORMS: list[tuple[str, str, int, str]] = [
    ("GitHub",        "https://github.com/{}",                   200, "Not Found"),
    ("GitLab",        "https://gitlab.com/{}",                   200, ""),
    ("Twitter/X",     "https://x.com/{}",                        200, "This account doesn't exist"),
    ("Instagram",     "https://www.instagram.com/{}/",           200, "Sorry, this page"),
    ("Reddit",        "https://www.reddit.com/user/{}/",         200, "page not found"),
    ("LinkedIn",      "https://www.linkedin.com/in/{}/",         200, ""),
    ("TikTok",        "https://www.tiktok.com/@{}",              200, "Couldn't find this account"),
    ("YouTube",       "https://www.youtube.com/@{}",             200, ""),
    ("Pinterest",     "https://www.pinterest.com/{}/",           200, ""),
    ("Twitch",        "https://www.twitch.tv/{}",                200, ""),
    ("Medium",        "https://medium.com/@{}",                  200, ""),
    ("Dev.to",        "https://dev.to/{}",                       200, ""),
    ("Keybase",       "https://keybase.io/{}",                   200, ""),
    ("HackerNews",    "https://news.ycombinator.com/user?id={}", 200, "No such user"),
    ("Steam",         "https://steamcommunity.com/id/{}",        200, "The specified profile could not be found"),
    ("Gravatar",      "https://gravatar.com/{}",                 200, ""),
    ("Pastebin",      "https://pastebin.com/u/{}",               200, ""),
    ("DockerHub",     "https://hub.docker.com/u/{}",             200, ""),
    ("npm",           "https://www.npmjs.com/~{}",               200, ""),
    ("PyPI",          "https://pypi.org/user/{}/",               200, ""),
]

_UA = "Mozilla/5.0 (compatible; hackingtool-osint/2.0)"


@dataclass
class PlatformResult:
    platform: str
    url: str
    found: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


@dataclass
class UsernameResult:
    username: str
    results: List[PlatformResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def found(self) -> list[PlatformResult]:
        return [r for r in self.results if r.found]

    @property
    def not_found(self) -> list[PlatformResult]:
        return [r for r in self.results if not r.found and r.error is None]


class UsernameOSINT:
    """Check username presence across popular platforms (passive HEAD/GET requests)."""

    def __init__(self, cfg: Optional[Config] = None):
        self.timeout = cfg.timeout if cfg else 8
        self.max_threads = cfg.max_threads if cfg else 20

    def check(self, username: str, show_all: bool = False) -> UsernameResult:
        username = username.strip()
        if not username:
            return UsernameResult(username=username, error="Username cannot be empty.")

        results: list[PlatformResult] = []
        with ThreadPoolExecutor(max_workers=min(self.max_threads, len(_PLATFORMS))) as pool:
            futures = {
                pool.submit(self._probe, username, name, tmpl, expected, fp): name
                for name, tmpl, expected, fp in _PLATFORMS
            }
            for fut in as_completed(futures):
                results.append(fut.result())

        results.sort(key=lambda r: (not r.found, r.platform))
        return UsernameResult(username=username, results=results)

    def _probe(self, username: str, name: str, tmpl: str, expected: int, fp: str) -> PlatformResult:
        url = tmpl.format(username)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read(4096).decode(errors="replace")
        except urllib.error.HTTPError as exc:
            return PlatformResult(platform=name, url=url, found=False, status_code=exc.code)
        except Exception as exc:
            return PlatformResult(platform=name, url=url, found=False, error=str(exc)[:60])

        found = (status == expected) and (not fp or fp.lower() not in body.lower())
        return PlatformResult(platform=name, url=url, found=found, status_code=status)
