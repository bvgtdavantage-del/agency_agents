import hashlib
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class HashMatch:
    algorithm: str
    confidence: str
    description: str


HASH_PATTERNS = [
    (r"^[a-f0-9]{32}$", "MD5", "high", "MD5 - 128-bit hash (insecure, avoid for passwords)"),
    (r"^[a-f0-9]{40}$", "SHA-1", "high", "SHA-1 - 160-bit hash (deprecated for security)"),
    (r"^[a-f0-9]{56}$", "SHA-224", "high", "SHA-224 - 224-bit SHA-2 hash"),
    (r"^[a-f0-9]{64}$", "SHA-256", "high", "SHA-256 - 256-bit SHA-2 hash"),
    (r"^[a-f0-9]{96}$", "SHA-384", "high", "SHA-384 - 384-bit SHA-2 hash"),
    (r"^[a-f0-9]{128}$", "SHA-512", "high", "SHA-512 - 512-bit SHA-2 hash"),
    (r"^\$2[aby]\$\d{2}\$.{53}$", "bcrypt", "high", "bcrypt - Adaptive password hashing"),
    (r"^\$argon2[id]{1,2}\$", "Argon2", "high", "Argon2 - Winner of Password Hashing Competition"),
    (r"^\$pbkdf2-sha\d+\$", "PBKDF2", "high", "PBKDF2 - Password-Based Key Derivation Function"),
    (r"^\$scrypt\$", "scrypt", "high", "scrypt - Memory-hard key derivation function"),
    (r"^[a-f0-9]{8}$", "CRC32", "medium", "CRC32 - Checksum (not a cryptographic hash)"),
    (r"^[a-f0-9]{16}$", "MD5-half/CRC64", "low", "Possible MD5 half or CRC64"),
    (r"^sha\d+\$.+\$.+$", "Django", "medium", "Django password hash format"),
    (r"^\*[A-F0-9]{40}$", "MySQL4.1+", "high", "MySQL 4.1+ password hash"),
]


class HashIdentifier:
    def identify(self, hash_value: str) -> list[HashMatch]:
        value = hash_value.strip()
        matches = []
        for pattern, algo, confidence, desc in HASH_PATTERNS:
            if re.match(pattern, value, re.IGNORECASE):
                matches.append(HashMatch(algo, confidence, desc))
        return matches

    def is_known_hash(self, value: str) -> bool:
        return len(self.identify(value)) > 0


class HashGenerator:
    ALGORITHMS = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512,
        "sha3_256": hashlib.sha3_256,
        "sha3_512": hashlib.sha3_512,
        "blake2b": hashlib.blake2b,
        "blake2s": hashlib.blake2s,
    }

    def generate(self, data: str, algorithm: str = "sha256") -> Optional[str]:
        algo = algorithm.lower().replace("-", "_")
        if algo not in self.ALGORITHMS:
            return None
        h = self.ALGORITHMS[algo](data.encode())
        return h.hexdigest()

    def generate_all(self, data: str) -> dict[str, str]:
        return {algo: self.ALGORITHMS[algo](data.encode()).hexdigest() for algo in self.ALGORITHMS}

    @property
    def supported_algorithms(self) -> list[str]:
        return list(self.ALGORITHMS.keys())
