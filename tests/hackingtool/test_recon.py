import pytest
import socket
from unittest.mock import patch, MagicMock
from hackingtool.modules.recon.whois_lookup import WhoisLookup, WhoisResult
from hackingtool.modules.recon.dns_enum import DNSEnumerator, DNSResult, DNSRecord
from hackingtool.modules.recon.port_scanner import PortScanner, ScanResult, COMMON_PORTS
from hackingtool.core.config import Config


class TestWhoisLookup:
    def setup_method(self):
        self.wl = WhoisLookup(Config(timeout=3))

    def test_result_has_domain(self):
        result = WhoisResult(domain="example.com")
        assert result.domain == "example.com"

    def test_result_success_when_no_error(self):
        result = WhoisResult(domain="example.com")
        assert result.success is True

    def test_result_failure_when_error_set(self):
        result = WhoisResult(domain="example.com", error="Connection refused")
        assert result.success is False

    def test_extract_field_finds_registrar(self):
        raw = "Domain Name: EXAMPLE.COM\nRegistrar: Example Registrar Inc.\n"
        result = self.wl._extract_field(raw, "Registrar")
        assert result == "Example Registrar Inc."

    def test_extract_field_returns_none_when_missing(self):
        raw = "Domain Name: EXAMPLE.COM\n"
        result = self.wl._extract_field(raw, "Registrar")
        assert result is None

    def test_extract_list_field_finds_multiple(self):
        raw = "Name Server: NS1.EXAMPLE.COM\nName Server: NS2.EXAMPLE.COM\n"
        result = self.wl._extract_list_field(raw, "Name Server")
        assert len(result) == 2
        assert "NS1.EXAMPLE.COM" in result

    def test_find_referred_server(self):
        raw = "refer: whois.verisign-grs.com\n"
        result = self.wl._find_referred_server(raw)
        assert result == "whois.verisign-grs.com"

    def test_lookup_failure_returns_error_result(self):
        with patch.object(self.wl, "_query", side_effect=Exception("Connection failed")):
            result = self.wl.lookup("fail.example")
        assert result.success is False
        assert "Connection failed" in result.error


class TestDNSEnumerator:
    def setup_method(self):
        self.dns = DNSEnumerator(Config(timeout=3))

    def test_result_has_domain(self):
        result = DNSResult(domain="example.com")
        assert result.domain == "example.com"

    def test_result_success_when_no_error(self):
        result = DNSResult(domain="example.com")
        assert result.success is True

    def test_result_failure_when_error_set(self):
        result = DNSResult(domain="example.com", error="fail")
        assert result.success is False

    def test_by_type_filters_correctly(self):
        result = DNSResult(domain="example.com", records=[
            DNSRecord("A", "1.2.3.4"),
            DNSRecord("MX", "mail.example.com"),
            DNSRecord("A", "5.6.7.8"),
        ])
        a_records = result.by_type("A")
        assert len(a_records) == 2
        assert all(r.record_type == "A" for r in a_records)

    def test_resolve_a_returns_records_for_known_host(self):
        with patch("socket.getaddrinfo", return_value=[
            (None, None, None, None, ("1.2.3.4", 0))
        ]):
            records = self.dns._resolve_a("example.com")
        assert len(records) == 1
        assert records[0].record_type == "A"
        assert records[0].value == "1.2.3.4"

    def test_resolve_a_returns_empty_on_error(self):
        with patch("socket.getaddrinfo", side_effect=socket.gaierror):
            records = self.dns._resolve_a("nonexistent.invalid")
        assert records == []

    def test_reverse_lookup_returns_hostname(self):
        with patch("socket.gethostbyaddr", return_value=("example.com", [], [])):
            result = self.dns.reverse_lookup("1.2.3.4")
        assert result == "example.com"

    def test_reverse_lookup_returns_none_on_failure(self):
        with patch("socket.gethostbyaddr", side_effect=socket.herror):
            result = self.dns.reverse_lookup("0.0.0.0")
        assert result is None


class TestPortScanner:
    def setup_method(self):
        self.scanner = PortScanner(Config(timeout=1, max_threads=10))

    def test_common_ports_dict_not_empty(self):
        assert len(COMMON_PORTS) > 10

    def test_scan_result_host_preserved(self):
        result = ScanResult(host="example.com", ip="1.2.3.4")
        assert result.host == "example.com"

    def test_scan_result_success_true_by_default(self):
        result = ScanResult(host="x", ip="1.2.3.4")
        assert result.success is True

    def test_scan_result_failure_when_error(self):
        result = ScanResult(host="x", ip=None, error="DNS failure")
        assert result.success is False

    def test_scan_open_port_detected(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"), \
             patch("socket.create_connection") as mock_conn:
            mock_sock = MagicMock()
            mock_sock.__enter__ = lambda s: s
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock.recv.return_value = b"SSH-2.0-OpenSSH\r\n"
            mock_conn.return_value = mock_sock

            result = self.scanner.scan("localhost", ports=[22])

        assert len(result.open_ports) == 1
        assert result.open_ports[0].port == 22
        assert result.open_ports[0].state == "open"

    def test_scan_returns_error_on_dns_failure(self):
        with patch("socket.gethostbyname", side_effect=socket.gaierror("DNS failed")):
            result = self.scanner.scan("nonexistent.invalid", ports=[80])
        assert result.success is False

    def test_scan_port_returns_none_on_refused(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            result = self.scanner._scan_port("127.0.0.1", 9999)
        assert result is None

    def test_scan_sorts_open_ports(self):
        with patch("socket.gethostbyname", return_value="127.0.0.1"), \
             patch.object(self.scanner, "_scan_port", side_effect=lambda h, p: (
                 MagicMock(port=p, state="open", service="test", banner=None) if p in (80, 22, 443) else None
             )):
            result = self.scanner.scan("localhost", ports=[443, 22, 80])

        ports = [p.port for p in result.open_ports]
        assert ports == sorted(ports)
