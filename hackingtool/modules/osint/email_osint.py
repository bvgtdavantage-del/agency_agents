"""Email format permutation generator and pattern guesser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# Common corporate email patterns, ordered by prevalence
_PATTERNS = [
    ("{first}.{last}",         "first.last"),
    ("{f}{last}",              "firstinitial+last"),
    ("{first}{l}",             "first+lastinitial"),
    ("{first}_{last}",         "first_last"),
    ("{first}",                "first"),
    ("{last}",                 "last"),
    ("{last}.{first}",         "last.first"),
    ("{last}{f}",              "last+firstinitial"),
    ("{f}.{last}",             "firstinitial.last"),
    ("{first}{last}",          "firstlast"),
    ("{last}{first}",          "lastfirst"),
    ("{first}-{last}",         "first-last"),
    ("{f}_{last}",             "firstinitial_last"),
]


@dataclass
class EmailGuess:
    pattern_label: str
    address: str
    confidence: str    # high / medium / low


@dataclass
class EmailResult:
    domain: str
    first: str
    last: str
    guesses: List[EmailGuess] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class EmailOSINT:
    """Generate email format permutations for a target name and domain."""

    # High-confidence patterns (top 3 most common in enterprise)
    _HIGH = {"first.last", "firstinitial+last", "first+lastinitial"}
    _MED  = {"first_last", "first", "last.first", "firstinitial.last"}

    def generate(self, domain: str, first: str, last: str) -> EmailResult:
        first = self._clean(first)
        last  = self._clean(last)
        if not first or not last:
            return EmailResult(domain=domain, first=first, last=last,
                               error="Both first and last name are required.")
        f = first[0]
        l = last[0]
        guesses: list[EmailGuess] = []
        for tmpl, label in _PATTERNS:
            local = tmpl.format(first=first, last=last, f=f, l=l)
            address = f"{local}@{domain}"
            conf = "high" if label in self._HIGH else "medium" if label in self._MED else "low"
            guesses.append(EmailGuess(pattern_label=label, address=address, confidence=conf))
        return EmailResult(domain=domain, first=first, last=last, guesses=guesses)

    @staticmethod
    def _clean(name: str) -> str:
        return re.sub(r"[^a-z]", "", name.lower().strip())
