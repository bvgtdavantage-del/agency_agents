import socket
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional
from hackingtool.core.config import Config


COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
}


@dataclass
class PortResult:
    port: int
    state: str
    service: str
    banner: Optional[str] = None


@dataclass
class ScanResult:
    host: str
    ip: Optional[str]
    open_ports: list[PortResult] = field(default_factory=list)
    filtered_ports: list[int] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class PortScanner:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    def _scan_port(self, host: str, port: int) -> Optional[PortResult]:
        try:
            with socket.create_connection((host, port), timeout=self.config.timeout) as sock:
                service = COMMON_PORTS.get(port, "unknown")
                banner = None
                try:
                    sock.settimeout(1)
                    banner = sock.recv(1024).decode(errors="replace").strip()
                except Exception:
                    pass
                return PortResult(port=port, state="open", service=service, banner=banner)
        except (socket.timeout, ConnectionRefusedError):
            return None
        except OSError:
            return None

    def scan(
        self,
        host: str,
        ports: Optional[list[int]] = None,
        port_range: Optional[tuple[int, int]] = None,
    ) -> ScanResult:
        ip = None
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror as exc:
            return ScanResult(host=host, ip=None, error=str(exc))

        if ports is None:
            if port_range:
                ports = list(range(port_range[0], port_range[1] + 1))
            else:
                ports = list(COMMON_PORTS.keys())

        result = ScanResult(host=host, ip=ip)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_threads) as executor:
            futures = {executor.submit(self._scan_port, ip, p): p for p in ports}
            for future in concurrent.futures.as_completed(futures):
                port_result = future.result()
                if port_result:
                    result.open_ports.append(port_result)

        result.open_ports.sort(key=lambda r: r.port)
        return result
