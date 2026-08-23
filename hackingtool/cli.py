import argparse
import sys
import json
from hackingtool.core import print_banner, Config, color, Colors
from hackingtool.core.utils import format_table


def _make_config(args: argparse.Namespace) -> Config:
    return Config(
        timeout=args.timeout,
        verbose=getattr(args, "verbose", False),
        max_threads=getattr(args, "threads", 100),
    )


# ---------- Recon ----------

def cmd_whois(args: argparse.Namespace) -> int:
    from hackingtool.modules.recon import WhoisLookup
    cfg = _make_config(args)
    print(color(f"[*] WHOIS lookup: {args.domain}", Colors.CYAN))
    result = WhoisLookup(cfg).lookup(args.domain)
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    rows = [
        ("Registrar", result.registrar or "N/A"),
        ("Created", result.creation_date or "N/A"),
        ("Expires", result.expiration_date or "N/A"),
        ("Name Servers", ", ".join(result.name_servers) or "N/A"),
        ("Status", ", ".join(result.status[:2]) or "N/A"),
    ]
    print(format_table(rows, ["Field", "Value"]))
    if args.raw:
        print(color("\n[+] Raw output:", Colors.DIM))
        print(result.raw)
    return 0


def cmd_dns(args: argparse.Namespace) -> int:
    from hackingtool.modules.recon import DNSEnumerator
    cfg = _make_config(args)
    print(color(f"[*] DNS enumeration: {args.domain}", Colors.CYAN))
    result = DNSEnumerator(cfg).enumerate(args.domain)
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    if not result.records:
        print(color("[!] No records found.", Colors.YELLOW))
        return 0
    rows = [(r.record_type, r.value) for r in result.records]
    print(format_table(rows, ["Type", "Value"]))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    from hackingtool.modules.recon import PortScanner
    cfg = _make_config(args)
    ports = None
    port_range = None
    if args.ports:
        ports = [int(p.strip()) for p in args.ports.split(",")]
    elif args.range:
        start, end = args.range.split("-")
        port_range = (int(start), int(end))

    print(color(f"[*] Port scanning: {args.host}", Colors.CYAN))
    result = PortScanner(cfg).scan(args.host, ports=ports, port_range=port_range)
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    print(color(f"[+] Host: {result.host} ({result.ip})", Colors.GREEN))
    if not result.open_ports:
        print(color("[!] No open ports found.", Colors.YELLOW))
        return 0
    rows = [(p.port, p.state, p.service, (p.banner or "")[:60]) for p in result.open_ports]
    print(format_table(rows, ["Port", "State", "Service", "Banner"]))
    return 0


# ---------- Web ----------

def cmd_headers(args: argparse.Namespace) -> int:
    from hackingtool.modules.web import HeaderAnalyzer
    cfg = _make_config(args)
    print(color(f"[*] Analyzing headers: {args.url}", Colors.CYAN))
    report = HeaderAnalyzer(cfg).analyze(args.url)
    if not report.success:
        print(color(f"[!] Warning: {report.error}", Colors.YELLOW))

    grade_color = Colors.GREEN if report.grade in ("A+", "A") else Colors.YELLOW if report.grade in ("B", "C") else Colors.RED
    print(color(f"\n[+] Security Grade: {report.grade}  (Score: {report.score}/100)", grade_color + Colors.BOLD))

    print(color("\n[+] Security Headers:", Colors.CYAN))
    rows = []
    for f in report.security_findings:
        status = color("PRESENT", Colors.GREEN) if f.present else color("MISSING", Colors.RED)
        rows.append((f.header, status, (f.value or "")[:50]))
    print(format_table(rows, ["Header", "Status", "Value"]))

    print(color("\n[!] Information Disclosure Headers:", Colors.YELLOW))
    risk_rows = []
    for f in report.risk_findings:
        status = color("EXPOSED", Colors.RED) if f.present else color("ok", Colors.GREEN)
        risk_rows.append((f.header, status, (f.value or "")[:50]))
    print(format_table(risk_rows, ["Header", "Status", "Value"]))
    return 0


def cmd_ssl(args: argparse.Namespace) -> int:
    from hackingtool.modules.web import SSLChecker
    cfg = _make_config(args)
    host = args.host
    port = args.port
    print(color(f"[*] SSL/TLS check: {host}:{port}", Colors.CYAN))
    report = SSLChecker(cfg).check(host, port)

    grade_color = Colors.GREEN if report.grade == "A" else Colors.YELLOW if report.grade in ("B", "C") else Colors.RED
    print(color(f"\n[+] SSL Grade: {report.grade}", grade_color + Colors.BOLD))

    if not report.success:
        print(color(f"[!] Error: {report.error}", Colors.RED))
        return 1

    rows = [
        ("TLS Version", report.version or "N/A"),
        ("Cipher Suite", report.cipher[0] if report.cipher else "N/A"),
        ("Subject CN", report.subject.get("commonName", "N/A")),
        ("Issuer CN", report.issuer.get("commonName", "N/A")),
        ("Valid From", str(report.not_before) if report.not_before else "N/A"),
        ("Valid Until", str(report.not_after) if report.not_after else "N/A"),
        ("Days Remaining", str(report.days_remaining) if report.days_remaining is not None else "N/A"),
        ("Expired", color("YES", Colors.RED) if report.expired else color("NO", Colors.GREEN)),
        ("Self-Signed", color("YES", Colors.RED) if report.self_signed else color("NO", Colors.GREEN)),
        ("Weak Cipher", color("YES", Colors.RED) if report.weak_cipher else color("NO", Colors.GREEN)),
    ]
    print(format_table(rows, ["Field", "Value"]))

    if report.san:
        print(color("\n[+] Subject Alternative Names:", Colors.CYAN))
        for san in report.san:
            print(f"  - {san}")
    return 0


# ---------- Crypto ----------

def cmd_hash_identify(args: argparse.Namespace) -> int:
    from hackingtool.modules.crypto import HashIdentifier
    print(color(f"[*] Identifying hash: {args.hash}", Colors.CYAN))
    matches = HashIdentifier().identify(args.hash)
    if not matches:
        print(color("[!] No matching hash type found.", Colors.YELLOW))
        return 1
    rows = [(m.algorithm, m.confidence, m.description) for m in matches]
    print(format_table(rows, ["Algorithm", "Confidence", "Description"]))
    return 0


def cmd_hash_generate(args: argparse.Namespace) -> int:
    from hackingtool.modules.crypto import HashGenerator
    gen = HashGenerator()
    if args.all:
        results = gen.generate_all(args.text)
        rows = [(algo, h) for algo, h in results.items()]
        print(format_table(rows, ["Algorithm", "Hash"]))
    else:
        algo = args.algorithm or "sha256"
        result = gen.generate(args.text, algo)
        if result is None:
            print(color(f"[!] Unknown algorithm: {algo}", Colors.RED))
            return 1
        print(color(f"[+] {algo.upper()}: ", Colors.GREEN) + result)
    return 0


def cmd_encode(args: argparse.Namespace) -> int:
    from hackingtool.modules.crypto import Encoder
    enc = Encoder()
    method = args.method
    data = args.data

    dispatch = {
        "b64e": lambda: enc.base64_encode(data),
        "b64d": lambda: enc.base64_decode(data).decode(errors="replace"),
        "hexe": lambda: enc.hex_encode(data),
        "hexd": lambda: enc.hex_decode(data).decode(errors="replace"),
        "urle": lambda: enc.url_encode(data),
        "urld": lambda: enc.url_decode(data),
        "htmle": lambda: enc.html_encode(data),
        "htmld": lambda: enc.html_decode(data),
        "rot13": lambda: enc.rot13(data),
        "bine": lambda: enc.to_binary(data),
        "bind": lambda: enc.from_binary(data),
        "smart": None,
    }

    if method == "smart":
        results = enc.smart_decode(data)
        if not results:
            print(color("[!] No successful decodings found.", Colors.YELLOW))
            return 1
        rows = [(fmt, val[:80]) for fmt, val in results.items()]
        print(format_table(rows, ["Format", "Decoded"]))
        return 0

    if method not in dispatch:
        print(color(f"[!] Unknown method: {method}", Colors.RED))
        print("Available: " + ", ".join(dispatch.keys()))
        return 1

    result = dispatch[method]()
    print(color("[+] Result: ", Colors.GREEN) + str(result))
    return 0


# ---------- OSINT ----------

def cmd_ip(args: argparse.Namespace) -> int:
    from hackingtool.modules.osint import IPLookup
    cfg = _make_config(args)
    lookup = IPLookup(cfg)

    if args.me:
        print(color("[*] Looking up your public IP...", Colors.CYAN))
        info = lookup.my_ip()
    else:
        print(color(f"[*] IP lookup: {args.target}", Colors.CYAN))
        info = lookup.lookup(args.target)

    if not info.success:
        print(color(f"[!] Error: {info.error}", Colors.RED))
        return 1

    if info.is_bogon:
        print(color(f"[!] {info.ip} is a private/bogon address.", Colors.YELLOW))
        return 0

    rows = [
        ("IP", info.ip),
        ("Hostname", info.hostname or "N/A"),
        ("City", info.city or "N/A"),
        ("Region", info.region or "N/A"),
        ("Country", f"{info.country} ({info.country_code})" if info.country else "N/A"),
        ("Organization", info.org or "N/A"),
        ("ISP", info.isp or "N/A"),
        ("Coordinates", info.coordinates or "N/A"),
        ("Timezone", info.timezone or "N/A"),
    ]
    print(format_table(rows, ["Field", "Value"]))
    return 0


# ---------- OSINT (extended) ----------

def cmd_certs(args: argparse.Namespace) -> int:
    from hackingtool.modules.osint import CertTransparency
    cfg = _make_config(args)
    print(color(f"[*] Certificate transparency lookup: {args.domain}", Colors.CYAN))
    result = CertTransparency(cfg).lookup(args.domain)
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    print(color(f"[+] Found {len(result.records)} certificate records, {len(result.subdomains)} unique subdomains", Colors.GREEN))
    if result.subdomains:
        print(color("\n[+] Subdomains:", Colors.CYAN))
        for sub in result.subdomains:
            print(f"  - {sub}")
    if args.records and result.records:
        print(color(f"\n[+] Certificate records (first {min(10, len(result.records))}):", Colors.CYAN))
        rows = [(r.domain[:50], r.issuer[:30], r.not_after[:10]) for r in result.records[:10]]
        print(format_table(rows, ["Domain", "Issuer", "Expires"]))
    return 0


def cmd_emails(args: argparse.Namespace) -> int:
    from hackingtool.modules.osint import EmailHarvester
    print(color(f"[*] Email pattern discovery: {args.domain}", Colors.CYAN))
    result = EmailHarvester().generate_patterns(
        args.domain,
        first_name=args.first,
        last_name=args.last,
    )
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    print(color("\n[+] Email format patterns:", Colors.CYAN))
    rows = [(p.format, p.example, p.confidence) for p in result.patterns]
    print(format_table(rows, ["Format", "Example", "Confidence"]))
    if args.samples and result.sample_emails:
        print(color(f"\n[+] Sample emails ({len(result.sample_emails)}):", Colors.CYAN))
        for email in result.sample_emails[:20]:
            print(f"  {email}")
    return 0


def cmd_username(args: argparse.Namespace) -> int:
    from hackingtool.modules.osint import UsernameChecker
    cfg = _make_config(args)
    print(color(f"[*] Username lookup: {args.username}", Colors.CYAN))
    print(color("[*] Checking platforms (this may take a moment)...", Colors.DIM))
    result = UsernameChecker(cfg).check(args.username)
    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1
    print(color(f"\n[+] Found on {result.found_count} platform(s):", Colors.GREEN + Colors.BOLD))
    if result.found:
        rows = [(r.platform, r.url) for r in result.found]
        print(format_table(rows, ["Platform", "URL"]))
    else:
        print(color("  No accounts found.", Colors.YELLOW))
    if args.show_all and result.not_found:
        print(color(f"\n[-] Not found on {len(result.not_found)} platform(s):", Colors.DIM))
        for r in result.not_found:
            print(f"  {r.platform}")
    return 0


def cmd_dorks(args: argparse.Namespace) -> int:
    from hackingtool.modules.osint import DorkGenerator
    print(color(f"[*] Generating Google dorks for: {args.domain}", Colors.CYAN))
    result = DorkGenerator().generate(args.domain)
    category = args.category
    queries = result.by_category(category) if category else result.queries
    print(color(f"\n[+] {len(queries)} dork queries generated:", Colors.GREEN))
    rows = [(q.category, q.query, q.description[:50]) for q in queries]
    print(format_table(rows, ["Category", "Query", "Description"]))
    return 0


# ---------- CTF ----------

def cmd_cipher(args: argparse.Namespace) -> int:
    from hackingtool.modules.ctf import CipherTools
    ct = CipherTools()
    method = args.method
    text = args.text

    if method == "caesar-brute":
        results = ct.caesar_brute(text)
        rows = [(str(s), r) for s, r in results]
        print(format_table(rows, ["Shift", "Result"]))
        return 0

    if method == "xor-brute":
        results = ct.xor_brute_single(text.encode())
        if not results:
            print(color("[!] No printable XOR results.", Colors.YELLOW))
            return 0
        rows = [(f"0x{k:02X}", v[:80]) for k, v in results]
        print(format_table(rows, ["Key", "Result"]))
        return 0

    dispatch = {
        "caesar": lambda: ct.caesar_encrypt(text, args.shift or 13),
        "caesar-d": lambda: ct.caesar_decrypt(text, args.shift or 13),
        "vigenere": lambda: ct.vigenere_encrypt(text, args.key or ""),
        "vigenere-d": lambda: ct.vigenere_decrypt(text, args.key or ""),
        "atbash": lambda: ct.atbash(text),
        "morse": lambda: ct.morse_encode(text),
        "morse-d": lambda: ct.morse_decode(text),
        "rot13": lambda: ct.caesar_encrypt(text, 13),
    }

    if method not in dispatch:
        print(color(f"[!] Unknown cipher: {method}", Colors.RED))
        print("Available: " + ", ".join(dispatch.keys()) + ", caesar-brute, xor-brute")
        return 1

    result = dispatch[method]()
    print(color("[+] Result: ", Colors.GREEN) + result)
    return 0


def cmd_pattern(args: argparse.Namespace) -> int:
    from hackingtool.modules.ctf import PatternSearch
    ps = PatternSearch()
    text = args.text
    matches = ps.search(text)
    if not matches:
        print(color("[!] No patterns found.", Colors.YELLOW))
        return 0
    rows = [(m.pattern_name, m.value[:60], str(m.start)) for m in matches]
    print(format_table(rows, ["Pattern", "Match", "Position"]))
    return 0


# ---------- Forensics ----------

def cmd_file_analyze(args: argparse.Namespace) -> int:
    from hackingtool.modules.forensics import FileAnalyzer
    import pathlib

    path = pathlib.Path(args.file)
    if not path.exists():
        print(color(f"[!] File not found: {args.file}", Colors.RED))
        return 1

    print(color(f"[*] Analyzing: {args.file}", Colors.CYAN))
    info = FileAnalyzer().analyze(path)

    if not info.success:
        print(color(f"[!] Error: {info.error}", Colors.RED))
        return 1

    rows = [
        ("Type", info.description),
        ("MIME", info.mime),
        ("Size", f"{info.size:,} bytes"),
        ("Entropy", f"{info.entropy:.4f}  ({info.entropy_label})"),
    ]
    print(format_table(rows, ["Field", "Value"]))

    if not args.no_strings and info.printable_strings:
        print(color(f"\n[+] Extracted strings ({len(info.printable_strings)}):", Colors.CYAN))
        for s in info.printable_strings:
            print(f"  {s}")

    if args.hex:
        print(color("\n[+] Hex preview:", Colors.CYAN))
        print(info.hex_preview)

    return 0


def cmd_steg_detect(args: argparse.Namespace) -> int:
    from hackingtool.modules.forensics import StegDetector
    import pathlib

    path = pathlib.Path(args.file)
    if not path.exists():
        print(color(f"[!] File not found: {args.file}", Colors.RED))
        return 1

    data = path.read_bytes()
    print(color(f"[*] Steganography scan: {args.file}", Colors.CYAN))
    result = StegDetector().detect(data, filename=args.file)

    if not result.success:
        print(color(f"[!] Error: {result.error}", Colors.RED))
        return 1

    verdict_color = Colors.RED if result.score >= 70 else Colors.YELLOW if result.score >= 35 else Colors.GREEN
    print(color(f"\n[+] Suspicion score: {result.score}/100", verdict_color + Colors.BOLD))
    print(color(f"[+] Verdict: {result.verdict}", verdict_color))

    if result.lsb_chi_p is not None:
        print(color(f"[+] LSB chi-square p-value: {result.lsb_chi_p:.4f}", Colors.CYAN))

    if result.appended_bytes:
        print(color(f"[!] Appended data: {result.appended_bytes} bytes after image end", Colors.RED))

    if result.indicators:
        print(color("\n[!] Indicators:", Colors.YELLOW))
        for ind in result.indicators:
            print(f"  - {ind}")
    else:
        print(color("[+] No steganography indicators found.", Colors.GREEN))

    return 0


# ---------- Argument Parser ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hackingtool",
        description="All-in-One Security Research Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--timeout", type=int, default=5, help="Connection timeout in seconds")
    parser.add_argument("--threads", type=int, default=100, help="Max concurrent threads")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-banner", action="store_true", help="Suppress banner")

    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # recon
    p_whois = sub.add_parser("whois", help="WHOIS domain lookup")
    p_whois.add_argument("domain")
    p_whois.add_argument("--raw", action="store_true", help="Show raw WHOIS output")
    p_whois.set_defaults(func=cmd_whois)

    p_dns = sub.add_parser("dns", help="DNS record enumeration")
    p_dns.add_argument("domain")
    p_dns.set_defaults(func=cmd_dns)

    p_scan = sub.add_parser("scan", help="TCP port scanner")
    p_scan.add_argument("host")
    p_scan.add_argument("-p", "--ports", help="Comma-separated ports (e.g. 80,443,8080)")
    p_scan.add_argument("-r", "--range", help="Port range (e.g. 1-1024)")
    p_scan.set_defaults(func=cmd_scan)

    # web
    p_headers = sub.add_parser("headers", help="HTTP security header analysis")
    p_headers.add_argument("url")
    p_headers.set_defaults(func=cmd_headers)

    p_ssl = sub.add_parser("ssl", help="SSL/TLS certificate checker")
    p_ssl.add_argument("host")
    p_ssl.add_argument("--port", type=int, default=443)
    p_ssl.set_defaults(func=cmd_ssl)

    # crypto
    p_hashid = sub.add_parser("hash-id", help="Identify hash type")
    p_hashid.add_argument("hash")
    p_hashid.set_defaults(func=cmd_hash_identify)

    p_hashgen = sub.add_parser("hash-gen", help="Generate hashes")
    p_hashgen.add_argument("text")
    p_hashgen.add_argument("-a", "--algorithm", default="sha256", help="Hash algorithm")
    p_hashgen.add_argument("--all", action="store_true", help="Generate with all algorithms")
    p_hashgen.set_defaults(func=cmd_hash_generate)

    p_enc = sub.add_parser("encode", help="Encode/decode data")
    p_enc.add_argument("method", choices=[
        "b64e", "b64d", "hexe", "hexd", "urle", "urld",
        "htmle", "htmld", "rot13", "bine", "bind", "smart"
    ])
    p_enc.add_argument("data")
    p_enc.set_defaults(func=cmd_encode)

    # osint
    p_ip = sub.add_parser("ip", help="IP/hostname geolocation lookup")
    p_ip.add_argument("target", nargs="?", help="IP address or hostname")
    p_ip.add_argument("--me", action="store_true", help="Look up your own public IP")
    p_ip.set_defaults(func=cmd_ip)

    p_certs = sub.add_parser("certs", help="Certificate transparency log lookup (passive subdomain discovery)")
    p_certs.add_argument("domain", help="Target domain (e.g. example.com)")
    p_certs.add_argument("--records", action="store_true", help="Show raw certificate records")
    p_certs.set_defaults(func=cmd_certs)

    p_emails = sub.add_parser("emails", help="Email format pattern discovery for a domain")
    p_emails.add_argument("domain", help="Target domain (e.g. example.com)")
    p_emails.add_argument("--first", help="First name for specific email generation")
    p_emails.add_argument("--last", help="Last name for specific email generation")
    p_emails.add_argument("--samples", action="store_true", help="Show sample emails")
    p_emails.set_defaults(func=cmd_emails)

    p_username = sub.add_parser("username", help="Check username across major platforms")
    p_username.add_argument("username", help="Username to investigate")
    p_username.add_argument("--show-all", action="store_true", help="Also show platforms where not found")
    p_username.set_defaults(func=cmd_username)

    p_dorks = sub.add_parser("dorks", help="Generate Google dork queries for passive recon")
    p_dorks.add_argument("domain", help="Target domain (e.g. example.com)")
    p_dorks.add_argument("--category", choices=[
        "exposed_files", "login_pages", "tech_stack",
        "subdomains", "sensitive_dirs", "emails", "code_repos"
    ], help="Filter by category")
    p_dorks.set_defaults(func=cmd_dorks)

    # ctf
    p_cipher = sub.add_parser("cipher", help="Classic cipher tools")
    p_cipher.add_argument("method", choices=[
        "caesar", "caesar-d", "caesar-brute",
        "vigenere", "vigenere-d",
        "atbash", "rot13",
        "morse", "morse-d",
        "xor-brute",
    ])
    p_cipher.add_argument("text")
    p_cipher.add_argument("-s", "--shift", type=int, default=13, help="Caesar shift value")
    p_cipher.add_argument("-k", "--key", help="Vigenere key")
    p_cipher.set_defaults(func=cmd_cipher)

    p_pattern = sub.add_parser("pattern", help="Search text for CTF patterns and secrets")
    p_pattern.add_argument("text")
    p_pattern.set_defaults(func=cmd_pattern)

    # forensics
    p_file = sub.add_parser("file-analyze", help="Identify file type, entropy, and extract strings")
    p_file.add_argument("file", help="Path to file")
    p_file.add_argument("--hex", action="store_true", help="Show hex preview")
    p_file.add_argument("--no-strings", action="store_true", help="Suppress string extraction")
    p_file.set_defaults(func=cmd_file_analyze)

    p_steg = sub.add_parser("steg-detect", help="Heuristic steganography detector (PNG/BMP/JPEG)")
    p_steg.add_argument("file", help="Path to image file")
    p_steg.set_defaults(func=cmd_steg_detect)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.no_banner:
        print_banner()

    if not args.command:
        parser.print_help()
        return 0

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
