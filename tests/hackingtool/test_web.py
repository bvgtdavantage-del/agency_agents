import pytest
from unittest.mock import patch, MagicMock
from hackingtool.modules.web.header_analyzer import HeaderAnalyzer, HeaderReport, SECURITY_HEADERS
from hackingtool.modules.web.ssl_checker import SSLChecker, SSLReport, WEAK_CIPHERS
from hackingtool.core.config import Config


class TestHeaderAnalyzer:
    def setup_method(self):
        self.analyzer = HeaderAnalyzer(Config(timeout=3))

    def test_report_grade_a_plus_on_high_score(self):
        report = HeaderReport(url="https://example.com", status_code=200, all_headers={}, score=95)
        assert report.grade == "A+"

    def test_report_grade_a_on_80(self):
        report = HeaderReport(url="https://example.com", status_code=200, all_headers={}, score=80)
        assert report.grade == "A"

    def test_report_grade_f_on_low_score(self):
        report = HeaderReport(url="https://example.com", status_code=200, all_headers={}, score=30)
        assert report.grade == "F"

    def test_report_success_when_no_error(self):
        report = HeaderReport(url="https://example.com", status_code=200, all_headers={})
        assert report.success is True

    def test_report_failure_when_error(self):
        report = HeaderReport(url="https://example.com", status_code=None, all_headers={}, error="timeout")
        assert report.success is False

    def test_analyze_adds_https_if_missing(self):
        with patch.object(self.analyzer, "_fetch_headers", return_value=(200, {})):
            report = self.analyzer.analyze("example.com")
        assert report.url.startswith("https://")

    def test_all_security_headers_assessed(self):
        with patch.object(self.analyzer, "_fetch_headers", return_value=(200, {
            "Strict-Transport-Security": "max-age=31536000",
        })):
            report = self.analyzer.analyze("https://example.com")
        assert len(report.security_findings) == len(SECURITY_HEADERS)

    def test_present_header_gives_score(self):
        headers = {h.lower(): "value" for h in SECURITY_HEADERS}
        with patch.object(self.analyzer, "_fetch_headers", return_value=(200, headers)):
            report = self.analyzer.analyze("https://example.com")
        assert report.score > 0

    def test_no_headers_gives_zero_score(self):
        with patch.object(self.analyzer, "_fetch_headers", return_value=(200, {})):
            report = self.analyzer.analyze("https://example.com")
        assert report.score == 0

    def test_server_header_flagged_as_risk(self):
        with patch.object(self.analyzer, "_fetch_headers", return_value=(200, {
            "Server": "Apache/2.4.51"
        })):
            report = self.analyzer.analyze("https://example.com")
        server_risks = [f for f in report.risk_findings if f.header == "Server"]
        assert len(server_risks) == 1
        assert server_risks[0].present is True

    def test_analyze_handles_network_error(self):
        with patch.object(self.analyzer, "_fetch_headers", side_effect=Exception("Network error")):
            report = self.analyzer.analyze("https://example.com")
        assert report.success is False


class TestSSLChecker:
    def setup_method(self):
        self.checker = SSLChecker(Config(timeout=3))

    def test_report_success_true_by_default(self):
        report = SSLReport(host="example.com", port=443)
        assert report.success is True

    def test_report_failure_when_error(self):
        report = SSLReport(host="example.com", port=443, error="SSL error")
        assert report.success is False

    def test_report_grade_f_when_error(self):
        report = SSLReport(host="example.com", port=443, error="Cert expired")
        assert report.grade == "F"

    def test_report_grade_f_when_expired(self):
        report = SSLReport(host="example.com", port=443, expired=True)
        assert report.grade == "F"

    def test_report_grade_c_when_self_signed(self):
        report = SSLReport(host="example.com", port=443, self_signed=True)
        assert report.grade == "C"

    def test_report_grade_c_when_weak_cipher(self):
        report = SSLReport(host="example.com", port=443, weak_cipher=True)
        assert report.grade == "C"

    def test_report_grade_a_when_good(self):
        import datetime
        report = SSLReport(
            host="example.com", port=443,
            expired=False, self_signed=False, weak_cipher=False,
            days_remaining=90,
            not_after=datetime.datetime.utcnow() + datetime.timedelta(days=90)
        )
        assert report.grade == "A"

    def test_coordinates_none_when_no_data(self):
        report = SSLReport(host="example.com", port=443)
        assert report.success is True

    def test_parse_dn_extracts_cn(self):
        dn = ((("commonName", "example.com"),),)
        result = self.checker._parse_dn(dn)
        assert result["commonName"] == "example.com"

    def test_is_weak_cipher_detects_rc4(self):
        assert self.checker._is_weak_cipher("RC4-SHA") is True

    def test_is_weak_cipher_detects_des(self):
        assert self.checker._is_weak_cipher("DES-CBC3-SHA") is True

    def test_is_weak_cipher_false_for_aes_gcm(self):
        assert self.checker._is_weak_cipher("ECDHE-RSA-AES256-GCM-SHA384") is False

    def test_check_handles_connection_error(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError):
            report = self.checker.check("127.0.0.1", port=9999)
        assert report.success is False
