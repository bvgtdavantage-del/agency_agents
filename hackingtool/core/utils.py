import re
import socket
from typing import Optional


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    PURPLE = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


def is_valid_ip(addr: str) -> bool:
    try:
        socket.inet_aton(addr)
        return True
    except socket.error:
        return False


def is_valid_domain(domain: str) -> bool:
    pattern = re.compile(
        r"^(?:[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
        r"[a-zA-Z]{2,}$"
    )
    return bool(pattern.match(domain))


def resolve_host(host: str) -> Optional[str]:
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def format_table(rows: list[tuple], headers: list[str]) -> str:
    all_rows = [headers] + [list(r) for r in rows]
    col_widths = [max(len(str(r[i])) for r in all_rows) for i in range(len(headers))]
    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    lines = [sep]
    for idx, row in enumerate(all_rows):
        line = "| " + " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(headers))) + " |"
        lines.append(line)
        if idx == 0:
            lines.append(sep)
    lines.append(sep)
    return "\n".join(lines)
