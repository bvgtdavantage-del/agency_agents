from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EmailPattern:
    format: str
    example: str
    confidence: str


@dataclass
class EmailResult:
    domain: str
    patterns: List[EmailPattern] = field(default_factory=list)
    sample_emails: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


_PATTERN_DEFS = [
    ("first.last",  "high"),
    ("flast",       "high"),
    ("f.last",      "high"),
    ("firstlast",   "medium"),
    ("first",       "medium"),
    ("last",        "medium"),
    ("first_last",  "medium"),
    ("lastf",       "medium"),
]

_SAMPLE_NAMES = [
    ("john", "smith"),
    ("jane", "doe"),
    ("alex", "taylor"),
]


def _render(fmt: str, first: str, last: str) -> str:
    return (
        fmt
        .replace("first", first)
        .replace("last", last)
        # Single-letter tokens must come after full-word replacements so that
        # "first" is not partially consumed when we resolve "f" separately.
        .replace("f", first[0])
    )


class EmailHarvester:
    def generate_patterns(
        self,
        domain: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> EmailResult:
        result = EmailResult(domain=domain)
        try:
            ref_first, ref_last = (
                (first_name.lower(), last_name.lower())
                if first_name and last_name
                else ("john", "smith")
            )

            for fmt, confidence in _PATTERN_DEFS:
                local = _render(fmt, ref_first, ref_last)
                result.patterns.append(EmailPattern(
                    format=fmt,
                    example=f"{local}@{domain}",
                    confidence=confidence,
                ))

            if first_name and last_name:
                f, l = first_name.lower(), last_name.lower()
                for fmt, _ in _PATTERN_DEFS:
                    result.sample_emails.append(f"{_render(fmt, f, l)}@{domain}")
            else:
                for f, l in _SAMPLE_NAMES:
                    for fmt, _ in _PATTERN_DEFS:
                        result.sample_emails.append(f"{_render(fmt, f, l)}@{domain}")

        except Exception as exc:
            result.error = str(exc)

        return result
