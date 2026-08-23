import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional

from hackingtool.core.config import Config


PLATFORMS = {
    "GitHub": "https://github.com/{username}",
    "Twitter": "https://twitter.com/{username}",
    "Instagram": "https://www.instagram.com/{username}/",
    "Reddit": "https://www.reddit.com/user/{username}",
    "LinkedIn": "https://www.linkedin.com/in/{username}",
    "TikTok": "https://www.tiktok.com/@{username}",
    "Pinterest": "https://www.pinterest.com/{username}",
    "Twitch": "https://www.twitch.tv/{username}",
    "YouTube": "https://www.youtube.com/@{username}",
    "Medium": "https://medium.com/@{username}",
    "Dev.to": "https://dev.to/{username}",
    "Keybase": "https://keybase.io/{username}",
    "HackerNews": "https://news.ycombinator.com/user?id={username}",
    "GitLab": "https://gitlab.com/{username}",
    "Pastebin": "https://pastebin.com/u/{username}",
}


@dataclass
class PlatformResult:
    platform: str
    url: str
    found: bool
    status_code: Optional[int] = None


@dataclass
class UsernameResult:
    username: str
    found: List[PlatformResult] = field(default_factory=list)
    not_found: List[PlatformResult] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def found_count(self) -> int:
        return len(self.found)


class UsernameChecker:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _check_platform(self, platform: str, url_template: str, username: str) -> PlatformResult:
        url = url_template.format(username=username)
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": self.config.user_agent},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                status_code = resp.status
        except urllib.error.HTTPError as exc:
            status_code = exc.code
        except Exception:
            # Fall back to GET on HEAD failure
            req = urllib.request.Request(
                url,
                headers={"User-Agent": self.config.user_agent},
            )
            try:
                with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                    status_code = resp.status
            except urllib.error.HTTPError as exc:
                status_code = exc.code
            except Exception:
                # Network-level failure: treat as not found, no status
                return PlatformResult(platform=platform, url=url, found=False, status_code=None)

        found = status_code == 200
        return PlatformResult(platform=platform, url=url, found=found, status_code=status_code)

    def check(self, username: str) -> UsernameResult:
        result = UsernameResult(username=username)

        max_workers = min(len(PLATFORMS), self.config.max_threads)
        futures = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for platform, url_template in PLATFORMS.items():
                future = executor.submit(self._check_platform, platform, url_template, username)
                futures[future] = platform

            for future in as_completed(futures):
                platform_result = future.result()
                if platform_result.found:
                    result.found.append(platform_result)
                else:
                    result.not_found.append(platform_result)

        # Sort for deterministic output
        result.found.sort(key=lambda r: r.platform)
        result.not_found.sort(key=lambda r: r.platform)

        return result
