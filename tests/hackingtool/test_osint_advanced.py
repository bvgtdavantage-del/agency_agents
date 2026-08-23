import json
import pytest
from unittest.mock import patch, MagicMock

from hackingtool.core.config import Config
from hackingtool.modules.osint.cert_transparency import CertTransparency, CertRecord, CertResult
from hackingtool.modules.osint.email_harvester import EmailHarvester, EmailPattern, EmailResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_urlopen_mock(payload):
    """Return a context-manager mock that yields JSON-encoded payload."""
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read.return_value = json.dumps(payload).encode()
    return mock_resp


_SAMPLE_CRT_RESPONSE = [
    {
        "name_value": "sub1.example.com",
        "issuer_name": "Let's Encrypt Authority X3",
        "issuer_ca_id": 16418,
        "not_before": "2024-01-01T00:00:00",
        "not_after": "2024-04-01T00:00:00",
        "serial_number": "AABBCC",
    },
    {
        "name_value": "*.example.com",
        "issuer_name": "DigiCert SHA2 Secure Server CA",
        "issuer_ca_id": 2422,
        "not_before": "2024-02-01T00:00:00",
        "not_after": "2025-02-01T00:00:00",
        "serial_number": "DDEEFF",
    },
    {
        "name_value": "sub2.example.com\nsub3.example.com",
        "issuer_name": "Sectigo RSA DV",
        "issuer_ca_id": 1234,
        "not_before": "2024-03-01T00:00:00",
        "not_after": "2025-03-01T00:00:00",
        "serial_number": "112233",
    },
    {
        "name_value": "unrelated.other.com",
        "issuer_name": "GlobalSign",
        "issuer_ca_id": 99,
        "not_before": "2024-01-15T00:00:00",
        "not_after": "2025-01-15T00:00:00",
        "serial_number": "445566",
    },
]


# ---------------------------------------------------------------------------
# CertResult dataclass
# ---------------------------------------------------------------------------

class TestCertResult:
    def test_success_true_when_no_error(self):
        result = CertResult(domain="example.com")
        assert result.success is True

    def test_success_false_when_error_set(self):
        result = CertResult(domain="example.com", error="timeout")
        assert result.success is False

    def test_default_records_and_subdomains_are_empty(self):
        result = CertResult(domain="example.com")
        assert result.records == []
        assert result.subdomains == []


# ---------------------------------------------------------------------------
# CertRecord dataclass
# ---------------------------------------------------------------------------

class TestCertRecord:
    def test_fields_stored(self):
        rec = CertRecord(
            domain="sub.example.com",
            issuer="Let's Encrypt",
            not_before="2024-01-01",
            not_after="2024-04-01",
            serial="AABBCC",
        )
        assert rec.domain == "sub.example.com"
        assert rec.issuer == "Let's Encrypt"
        assert rec.serial == "AABBCC"


# ---------------------------------------------------------------------------
# CertTransparency._extract_subdomains
# ---------------------------------------------------------------------------

class TestExtractSubdomains:
    def setup_method(self):
        self.ct = CertTransparency(Config(timeout=3))

    def test_plain_subdomain_included(self):
        records = [CertRecord("sub.example.com", "CA", "", "", "")]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert "sub.example.com" in subs

    def test_wildcard_stripped_to_bare_domain(self):
        records = [CertRecord("*.example.com", "CA", "", "", "")]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert "example.com" in subs
        assert "*.example.com" not in subs

    def test_unrelated_domain_excluded(self):
        records = [CertRecord("unrelated.other.com", "CA", "", "", "")]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert "unrelated.other.com" not in subs

    def test_multiline_san_split_correctly(self):
        records = [CertRecord("sub2.example.com\nsub3.example.com", "CA", "", "", "")]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert "sub2.example.com" in subs
        assert "sub3.example.com" in subs

    def test_subdomains_are_sorted(self):
        records = [
            CertRecord("z.example.com", "CA", "", "", ""),
            CertRecord("a.example.com", "CA", "", "", ""),
        ]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert subs == sorted(subs)

    def test_duplicates_removed(self):
        records = [
            CertRecord("sub.example.com", "CA", "", "", ""),
            CertRecord("sub.example.com", "CA", "", "", ""),
        ]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert subs.count("sub.example.com") == 1

    def test_case_normalised_to_lowercase(self):
        records = [CertRecord("SUB.EXAMPLE.COM", "CA", "", "", "")]
        subs = self.ct._extract_subdomains(records, "example.com")
        assert "sub.example.com" in subs


# ---------------------------------------------------------------------------
# CertTransparency.lookup (mocked HTTP)
# ---------------------------------------------------------------------------

class TestCertTransparencyLookup:
    def setup_method(self):
        self.ct = CertTransparency(Config(timeout=3))

    def test_lookup_returns_cert_result(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert isinstance(result, CertResult)

    def test_lookup_success_on_valid_response(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert result.success is True

    def test_lookup_parses_all_records(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert len(result.records) == len(_SAMPLE_CRT_RESPONSE)

    def test_lookup_record_fields_populated(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        rec = result.records[0]
        assert rec.domain == "sub1.example.com"
        assert rec.issuer == "Let's Encrypt Authority X3"
        assert rec.serial == "AABBCC"

    def test_lookup_extracts_subdomains(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert "sub1.example.com" in result.subdomains
        assert "sub2.example.com" in result.subdomains
        assert "sub3.example.com" in result.subdomains

    def test_lookup_excludes_unrelated_domains(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert "unrelated.other.com" not in result.subdomains

    def test_lookup_wildcard_becomes_base_domain(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(_SAMPLE_CRT_RESPONSE)):
            result = self.ct.lookup("example.com")
        assert "example.com" in result.subdomains

    def test_lookup_empty_response_gives_empty_results(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock([])):
            result = self.ct.lookup("example.com")
        assert result.success is True
        assert result.records == []
        assert result.subdomains == []

    def test_lookup_network_error_sets_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = self.ct.lookup("example.com")
        assert result.success is False
        assert "connection refused" in result.error

    def test_lookup_timeout_error_sets_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = self.ct.lookup("example.com")
        assert result.success is False

    def test_lookup_domain_stored_on_result(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock([])):
            result = self.ct.lookup("example.com")
        assert result.domain == "example.com"

    def test_lookup_uses_configured_user_agent(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock([])) as mock_open:
            self.ct.lookup("example.com")
        call_args = mock_open.call_args
        req = call_args[0][0]
        assert req.get_header("User-agent") == self.ct.config.user_agent


# ---------------------------------------------------------------------------
# EmailResult dataclass
# ---------------------------------------------------------------------------

class TestEmailResult:
    def test_success_true_when_no_error(self):
        result = EmailResult(domain="example.com")
        assert result.success is True

    def test_success_false_when_error_set(self):
        result = EmailResult(domain="example.com", error="bad domain")
        assert result.success is False

    def test_defaults_are_empty_lists(self):
        result = EmailResult(domain="example.com")
        assert result.patterns == []
        assert result.sample_emails == []


# ---------------------------------------------------------------------------
# EmailHarvester.generate_patterns — pure logic, no mocking needed
# ---------------------------------------------------------------------------

class TestEmailHarvesterPatterns:
    def setup_method(self):
        self.harvester = EmailHarvester()

    def test_returns_email_result(self):
        result = self.harvester.generate_patterns("example.com")
        assert isinstance(result, EmailResult)

    def test_success_on_valid_domain(self):
        result = self.harvester.generate_patterns("example.com")
        assert result.success is True

    def test_domain_stored_on_result(self):
        result = self.harvester.generate_patterns("acme.io")
        assert result.domain == "acme.io"

    def test_all_eight_formats_generated(self):
        result = self.harvester.generate_patterns("example.com")
        assert len(result.patterns) == 8

    def test_pattern_format_names_present(self):
        result = self.harvester.generate_patterns("example.com")
        fmt_names = {p.format for p in result.patterns}
        assert "first.last" in fmt_names
        assert "flast" in fmt_names
        assert "f.last" in fmt_names
        assert "firstlast" in fmt_names
        assert "first" in fmt_names
        assert "last" in fmt_names
        assert "first_last" in fmt_names
        assert "lastf" in fmt_names

    def test_high_confidence_formats(self):
        result = self.harvester.generate_patterns("example.com")
        high = {p.format for p in result.patterns if p.confidence == "high"}
        assert high == {"first.last", "flast", "f.last"}

    def test_medium_confidence_formats(self):
        result = self.harvester.generate_patterns("example.com")
        medium = {p.format for p in result.patterns if p.confidence == "medium"}
        assert medium == {"firstlast", "first", "last", "first_last", "lastf"}

    def test_pattern_examples_contain_domain(self):
        result = self.harvester.generate_patterns("corp.com")
        for pattern in result.patterns:
            assert "@corp.com" in pattern.example

    def test_first_last_format_example(self):
        result = self.harvester.generate_patterns("example.com")
        p = next(p for p in result.patterns if p.format == "first.last")
        assert "." in p.example.split("@")[0]
        assert "@example.com" in p.example

    def test_with_names_generates_specific_samples(self):
        result = self.harvester.generate_patterns("example.com", first_name="Alice", last_name="Brown")
        assert any("alice.brown@example.com" == e for e in result.sample_emails)
        assert any("abrown@example.com" == e for e in result.sample_emails)
        assert any("a.brown@example.com" == e for e in result.sample_emails)

    def test_with_names_sample_count_equals_format_count(self):
        result = self.harvester.generate_patterns("example.com", first_name="Bob", last_name="Jones")
        assert len(result.sample_emails) == 8

    def test_without_names_uses_multiple_sample_names(self):
        result = self.harvester.generate_patterns("example.com")
        # 3 sample name pairs × 8 formats
        assert len(result.sample_emails) == 24

    def test_without_names_samples_contain_domain(self):
        result = self.harvester.generate_patterns("myco.net")
        for email in result.sample_emails:
            assert "@myco.net" in email

    def test_names_are_lowercased(self):
        result = self.harvester.generate_patterns("example.com", first_name="JOHN", last_name="SMITH")
        assert all(e == e.lower() for e in result.sample_emails)

    def test_first_last_sample_format_correct(self):
        result = self.harvester.generate_patterns("example.com", first_name="john", last_name="smith")
        assert "john.smith@example.com" in result.sample_emails

    def test_flast_sample_format_correct(self):
        result = self.harvester.generate_patterns("example.com", first_name="john", last_name="smith")
        assert "jsmith@example.com" in result.sample_emails

    def test_f_dot_last_sample_format_correct(self):
        result = self.harvester.generate_patterns("example.com", first_name="john", last_name="smith")
        assert "j.smith@example.com" in result.sample_emails

    def test_lastf_sample_format_correct(self):
        result = self.harvester.generate_patterns("example.com", first_name="john", last_name="smith")
        assert "smithj@example.com" in result.sample_emails

    def test_first_underscore_last_sample_format_correct(self):
        result = self.harvester.generate_patterns("example.com", first_name="john", last_name="smith")
        assert "john_smith@example.com" in result.sample_emails
