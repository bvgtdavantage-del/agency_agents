"""Tests for new OSINT modules: cert_transparency, email_osint, username_osint, dork_generator."""

from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from hackingtool.modules.osint.cert_transparency import CertTransparency, CertResult
from hackingtool.modules.osint.email_osint import EmailOSINT, EmailResult
from hackingtool.modules.osint.username_osint import UsernameOSINT, UsernameResult, PlatformResult
from hackingtool.modules.osint.dork_generator import DorkGenerator, DorkResult, CATEGORIES


# ---------------------------------------------------------------------------
# CertTransparency
# ---------------------------------------------------------------------------

class TestCertTransparency:
    def setup_method(self):
        self.ct = CertTransparency()

    def _mock_response(self, data: list) -> MagicMock:
        m = MagicMock()
        m.read.return_value = json.dumps(data).encode()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    def test_query_returns_subdomains(self):
        payload = [
            {"name_value": "www.example.com"},
            {"name_value": "mail.example.com"},
            {"name_value": "api.example.com"},
        ]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert result.success
        assert "www.example.com" in result.subdomains
        assert "mail.example.com" in result.subdomains
        assert "api.example.com" in result.subdomains

    def test_query_deduplicates_subdomains(self):
        payload = [
            {"name_value": "www.example.com"},
            {"name_value": "www.example.com"},
            {"name_value": "*.example.com"},
        ]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert result.subdomains.count("www.example.com") == 1

    def test_query_strips_wildcard_prefix(self):
        payload = [{"name_value": "*.sub.example.com"}]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert all(not s.startswith("*") for s in result.subdomains)

    def test_query_returns_sorted_subdomains(self):
        payload = [
            {"name_value": "z.example.com"},
            {"name_value": "a.example.com"},
            {"name_value": "m.example.com"},
        ]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert result.subdomains == sorted(result.subdomains)

    def test_query_sets_total_certs(self):
        payload = [{"name_value": "a.example.com"}] * 5
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert result.total_certs == 5

    def test_query_network_error_returns_failure(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = self.ct.query("example.com")
        assert not result.success
        assert result.error is not None

    def test_query_empty_response(self):
        with patch("urllib.request.urlopen", return_value=self._mock_response([])):
            result = self.ct.query("example.com")
        assert result.success
        assert result.subdomains == []
        assert result.total_certs == 0

    def test_query_filters_unrelated_domains(self):
        payload = [
            {"name_value": "www.example.com"},
            {"name_value": "www.otherdomain.com"},
        ]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert all("example.com" in s for s in result.subdomains)

    def test_query_handles_multiline_name_value(self):
        payload = [{"name_value": "a.example.com\nb.example.com"}]
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = self.ct.query("example.com")
        assert "a.example.com" in result.subdomains
        assert "b.example.com" in result.subdomains


# ---------------------------------------------------------------------------
# EmailOSINT
# ---------------------------------------------------------------------------

class TestEmailOSINT:
    def setup_method(self):
        self.eo = EmailOSINT()

    def test_generates_first_dot_last(self):
        r = self.eo.generate("example.com", "John", "Smith")
        addresses = [g.address for g in r.guesses]
        assert "john.smith@example.com" in addresses

    def test_generates_firstinitial_last(self):
        r = self.eo.generate("example.com", "John", "Smith")
        addresses = [g.address for g in r.guesses]
        assert "jsmith@example.com" in addresses

    def test_generates_first_lastinitial(self):
        r = self.eo.generate("example.com", "John", "Smith")
        addresses = [g.address for g in r.guesses]
        assert "johns@example.com" in addresses

    def test_high_confidence_includes_top_patterns(self):
        r = self.eo.generate("example.com", "John", "Smith")
        high = [g for g in r.guesses if g.confidence == "high"]
        assert len(high) >= 2

    def test_cleans_uppercase_names(self):
        r = self.eo.generate("example.com", "JOHN", "SMITH")
        addresses = [g.address for g in r.guesses]
        assert all(a == a.lower() for a in addresses)

    def test_cleans_special_characters(self):
        r = self.eo.generate("example.com", "Jean-Pierre", "O'Brien")
        assert r.success
        assert all("@" in g.address for g in r.guesses)

    def test_empty_first_name_returns_error(self):
        r = self.eo.generate("example.com", "", "Smith")
        assert not r.success
        assert r.error is not None

    def test_empty_last_name_returns_error(self):
        r = self.eo.generate("example.com", "John", "")
        assert not r.success

    def test_returns_correct_domain(self):
        r = self.eo.generate("mycompany.org", "Alice", "Wong")
        assert all(g.address.endswith("@mycompany.org") for g in r.guesses)

    def test_guesses_have_pattern_labels(self):
        r = self.eo.generate("example.com", "John", "Smith")
        assert all(g.pattern_label for g in r.guesses)

    def test_all_guesses_are_valid_email_format(self):
        r = self.eo.generate("example.com", "John", "Smith")
        for g in r.guesses:
            assert "@" in g.address
            local, domain = g.address.split("@", 1)
            assert local
            assert domain == "example.com"


# ---------------------------------------------------------------------------
# UsernameOSINT
# ---------------------------------------------------------------------------

class TestUsernameOSINT:
    def setup_method(self):
        self.uo = UsernameOSINT()

    def _make_response(self, status: int, body: bytes = b"") -> MagicMock:
        m = MagicMock()
        m.status = status
        m.read.return_value = body
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    def test_empty_username_returns_error(self):
        result = self.uo.check("")
        assert not result.success
        assert result.error is not None

    def test_found_when_200_no_false_positive(self):
        with patch("urllib.request.urlopen", return_value=self._make_response(200, b"profile page")):
            result = self.uo.check("testuser")
        assert result.success
        assert len(result.found) > 0

    def test_not_found_when_404(self):
        err = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
        with patch("urllib.request.urlopen", side_effect=err):
            result = self.uo.check("nonexistentuser12345")
        assert result.success
        assert len(result.found) == 0

    def test_error_recorded_on_network_failure(self):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            result = self.uo.check("testuser")
        assert result.success
        errored = [r for r in result.results if r.error]
        assert len(errored) > 0

    def test_false_positive_string_marks_not_found(self):
        body = b"This account doesn't exist"
        with patch("urllib.request.urlopen", return_value=self._make_response(200, body)):
            result = self.uo.check("testuser")
        assert result.success
        twitter = next((r for r in result.results if "Twitter" in r.platform), None)
        if twitter:
            assert not twitter.found

    def test_results_sorted_found_first(self):
        responses = [
            self._make_response(200, b"profile"),
            urllib.error.HTTPError(url="", code=404, msg="", hdrs=None, fp=None),
        ]
        call_count = 0
        def side_effect(*a, **kw):
            nonlocal call_count
            r = responses[call_count % len(responses)]
            call_count += 1
            if isinstance(r, Exception):
                raise r
            return r
        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = self.uo.check("testuser")
        found_indices = [i for i, r in enumerate(result.results) if r.found]
        not_found_indices = [i for i, r in enumerate(result.results) if not r.found]
        if found_indices and not_found_indices:
            assert max(found_indices) < max(not_found_indices) or min(found_indices) < min(not_found_indices)

    def test_result_contains_url(self):
        with patch("urllib.request.urlopen", return_value=self._make_response(200, b"page")):
            result = self.uo.check("testuser")
        for r in result.results:
            assert r.url.startswith("http")


# ---------------------------------------------------------------------------
# DorkGenerator
# ---------------------------------------------------------------------------

class TestDorkGenerator:
    def setup_method(self):
        self.dg = DorkGenerator()

    def test_general_category_returns_dorks(self):
        r = self.dg.generate("example.com", "general")
        assert r.success
        assert len(r.dorks) > 0

    def test_dorks_contain_domain(self):
        r = self.dg.generate("example.com", "general")
        for d in r.dorks:
            assert "example.com" in d.query

    def test_all_category_returns_all_dorks(self):
        r_all = self.dg.generate("example.com", "all")
        r_gen = self.dg.generate("example.com", "general")
        assert len(r_all.dorks) > len(r_gen.dorks)

    def test_exposed_files_category(self):
        r = self.dg.generate("example.com", "exposed_files")
        assert r.success
        queries = [d.query for d in r.dorks]
        assert any("ext:" in q for q in queries)

    def test_login_pages_category(self):
        r = self.dg.generate("example.com", "login_pages")
        assert r.success
        queries = [d.query for d in r.dorks]
        assert any("login" in q or "admin" in q for q in queries)

    def test_subdomains_category(self):
        r = self.dg.generate("example.com", "subdomains")
        assert r.success
        queries = [d.query for d in r.dorks]
        assert any("*." in q for q in queries)

    def test_sensitive_data_category(self):
        r = self.dg.generate("example.com", "sensitive_data")
        assert r.success

    def test_technology_category(self):
        r = self.dg.generate("example.com", "technology")
        assert r.success

    def test_invalid_category_returns_error(self):
        r = self.dg.generate("example.com", "nonexistent_category")
        assert not r.success
        assert r.error is not None

    def test_dorks_have_descriptions(self):
        r = self.dg.generate("example.com", "general")
        assert all(d.description for d in r.dorks)

    def test_dorks_have_search_urls(self):
        r = self.dg.generate("example.com", "general")
        assert all(d.search_url.startswith("https://www.google.com") for d in r.dorks)

    def test_categories_list_is_populated(self):
        assert len(CATEGORIES) >= 5
        assert "general" in CATEGORIES
        assert "exposed_files" in CATEGORIES

    def test_domain_with_protocol_stripped(self):
        r = self.dg.generate("https://example.com", "general")
        assert r.success
        for d in r.dorks:
            assert "https://" not in d.query

    def test_search_url_is_url_encoded(self):
        r = self.dg.generate("example.com", "general")
        for d in r.dorks:
            assert " " not in d.search_url
