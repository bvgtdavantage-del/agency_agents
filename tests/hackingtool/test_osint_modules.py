"""Tests for username_checker and dork_generator OSINT modules."""
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from hackingtool.core.config import Config
from hackingtool.modules.osint.dork_generator import (
    ALL_CATEGORIES,
    DorkGenerator,
    DorkQuery,
    DorkResult,
)
from hackingtool.modules.osint.username_checker import (
    PLATFORMS,
    PlatformResult,
    UsernameChecker,
    UsernameResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_http_response(status: int) -> MagicMock:
    """Return a mock that behaves like the context-manager from urlopen."""
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ---------------------------------------------------------------------------
# PlatformResult dataclass
# ---------------------------------------------------------------------------

class TestPlatformResult:
    def test_found_true(self):
        r = PlatformResult(platform="GitHub", url="https://github.com/alice", found=True, status_code=200)
        assert r.found is True
        assert r.status_code == 200

    def test_found_false(self):
        r = PlatformResult(platform="GitHub", url="https://github.com/alice", found=False, status_code=404)
        assert r.found is False

    def test_status_code_optional(self):
        r = PlatformResult(platform="GitHub", url="https://github.com/alice", found=False)
        assert r.status_code is None


# ---------------------------------------------------------------------------
# UsernameResult dataclass
# ---------------------------------------------------------------------------

class TestUsernameResult:
    def _make_result(self, found_count: int, not_found_count: int, error=None) -> UsernameResult:
        found = [
            PlatformResult(platform=f"P{i}", url=f"https://p{i}.com/user", found=True, status_code=200)
            for i in range(found_count)
        ]
        not_found = [
            PlatformResult(platform=f"Q{i}", url=f"https://q{i}.com/user", found=False, status_code=404)
            for i in range(not_found_count)
        ]
        return UsernameResult(username="alice", found=found, not_found=not_found, error=error)

    def test_success_true_when_no_error(self):
        result = self._make_result(3, 2)
        assert result.success is True

    def test_success_false_when_error(self):
        result = self._make_result(0, 0, error="Something went wrong")
        assert result.success is False

    def test_found_count_matches_found_list(self):
        result = self._make_result(5, 3)
        assert result.found_count == 5

    def test_found_count_zero_when_none_found(self):
        result = self._make_result(0, 10)
        assert result.found_count == 0

    def test_username_stored(self):
        result = UsernameResult(username="testuser")
        assert result.username == "testuser"

    def test_default_lists_are_empty(self):
        result = UsernameResult(username="testuser")
        assert result.found == []
        assert result.not_found == []


# ---------------------------------------------------------------------------
# UsernameChecker — check() with mocked network
# ---------------------------------------------------------------------------

class TestUsernameCheckerFound:
    """Platform returns HTTP 200 → result should be in found list."""

    def setup_method(self):
        self.checker = UsernameChecker(Config(timeout=3, max_threads=4))

    def test_200_status_puts_platform_in_found(self):
        mock_resp = _make_http_response(200)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.checker.check("alice")

        assert result.success is True
        assert result.found_count == len(PLATFORMS)
        assert result.not_found == []

    def test_found_results_contain_correct_username_in_url(self):
        mock_resp = _make_http_response(200)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.checker.check("alice")

        for pr in result.found:
            assert "alice" in pr.url

    def test_found_results_sorted_by_platform_name(self):
        mock_resp = _make_http_response(200)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.checker.check("alice")

        names = [pr.platform for pr in result.found]
        assert names == sorted(names)


class TestUsernameCheckerNotFound:
    """Platform returns HTTP 404 → result should be in not_found list."""

    def setup_method(self):
        self.checker = UsernameChecker(Config(timeout=3, max_threads=4))

    def test_404_status_puts_platform_in_not_found(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            result = self.checker.check("nobody_xyz_123")

        assert result.success is True
        assert result.found_count == 0
        assert len(result.not_found) == len(PLATFORMS)

    def test_not_found_results_sorted_by_platform_name(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
        )):
            result = self.checker.check("nobody_xyz_123")

        names = [pr.platform for pr in result.not_found]
        assert names == sorted(names)

    def test_non_200_non_404_treated_as_not_found(self):
        """Redirects (301/302) and other codes are treated as not found."""
        mock_resp = _make_http_response(302)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = self.checker.check("alice")

        assert result.found_count == 0
        assert len(result.not_found) == len(PLATFORMS)


class TestUsernameCheckerNetworkErrors:
    """Network failures should be handled per-platform without crashing."""

    def setup_method(self):
        self.checker = UsernameChecker(Config(timeout=3, max_threads=4))

    def test_connection_error_does_not_raise(self):
        with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
            result = self.checker.check("alice")

        # Should succeed at the result level; all platforms land in not_found
        assert result.success is True
        assert result.found_count == 0
        assert len(result.not_found) == len(PLATFORMS)

    def test_timeout_error_does_not_raise(self):
        import socket
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            result = self.checker.check("alice")

        assert result.success is True

    def test_platform_with_network_error_has_no_status_code(self):
        with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
            result = self.checker.check("alice")

        for pr in result.not_found:
            assert pr.status_code is None

    def test_mixed_responses_partial_found(self):
        """Some platforms found (200), some not found (404), some error."""
        platforms_list = list(PLATFORMS.items())
        call_count = [0]

        def side_effect(req, timeout=None):
            idx = call_count[0] % 3
            call_count[0] += 1
            if idx == 0:
                return _make_http_response(200)
            elif idx == 1:
                raise urllib.error.HTTPError(
                    url="https://example.com", code=404, msg="Not Found", hdrs=None, fp=None
                )
            else:
                raise OSError("Network error")

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = self.checker.check("alice")

        total = len(result.found) + len(result.not_found)
        assert total == len(PLATFORMS)
        assert result.success is True

    def test_result_username_preserved_on_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("down")):
            result = self.checker.check("targetuser")

        assert result.username == "targetuser"


class TestUsernameCheckerConfig:
    def test_default_config_used_when_none_provided(self):
        checker = UsernameChecker()
        assert checker.config is not None

    def test_custom_config_stored(self):
        cfg = Config(timeout=10, max_threads=5)
        checker = UsernameChecker(cfg)
        assert checker.config.timeout == 10
        assert checker.config.max_threads == 5

    def test_user_agent_sent_in_request(self):
        cfg = Config(user_agent="TestAgent/1.0")
        checker = UsernameChecker(cfg)
        captured_requests = []

        def capture(req, timeout=None):
            captured_requests.append(req)
            return _make_http_response(200)

        with patch("urllib.request.urlopen", side_effect=capture):
            checker.check("alice")

        for req in captured_requests:
            assert req.get_header("User-agent") == "TestAgent/1.0"


# ---------------------------------------------------------------------------
# DorkQuery dataclass
# ---------------------------------------------------------------------------

class TestDorkQuery:
    def test_fields_stored(self):
        dq = DorkQuery(
            category="exposed_files",
            description="PDF files on example.com",
            query="site:example.com filetype:pdf",
        )
        assert dq.category == "exposed_files"
        assert dq.description == "PDF files on example.com"
        assert dq.query == "site:example.com filetype:pdf"


# ---------------------------------------------------------------------------
# DorkResult dataclass
# ---------------------------------------------------------------------------

class TestDorkResult:
    def _make_result(self) -> DorkResult:
        return DorkGenerator().generate("example.com")

    def test_target_stored(self):
        result = self._make_result()
        assert result.target == "example.com"

    def test_queries_is_non_empty_list(self):
        result = self._make_result()
        assert isinstance(result.queries, list)
        assert len(result.queries) > 0

    def test_all_queries_returns_strings(self):
        result = self._make_result()
        queries = result.all_queries()
        assert all(isinstance(q, str) for q in queries)

    def test_all_queries_length_matches_queries(self):
        result = self._make_result()
        assert len(result.all_queries()) == len(result.queries)

    def test_by_category_filters_correctly(self):
        result = self._make_result()
        pdf_queries = result.by_category("exposed_files")
        assert all(q.category == "exposed_files" for q in pdf_queries)

    def test_by_category_unknown_returns_empty(self):
        result = self._make_result()
        assert result.by_category("nonexistent_category") == []

    def test_default_queries_list_is_empty_for_bare_dataclass(self):
        result = DorkResult(target="example.com")
        assert result.queries == []
        assert result.all_queries() == []
        assert result.by_category("exposed_files") == []


# ---------------------------------------------------------------------------
# DorkGenerator — category coverage
# ---------------------------------------------------------------------------

class TestDorkGeneratorCategories:
    def setup_method(self):
        self.gen = DorkGenerator()
        self.result = self.gen.generate("example.com")
        self.present_categories = {q.category for q in self.result.queries}

    def test_all_required_categories_present(self):
        for cat in ALL_CATEGORIES:
            assert cat in self.present_categories, f"Category '{cat}' missing from generated dorks"

    def test_exposed_files_category_present(self):
        assert "exposed_files" in self.present_categories

    def test_login_pages_category_present(self):
        assert "login_pages" in self.present_categories

    def test_tech_stack_category_present(self):
        assert "tech_stack" in self.present_categories

    def test_subdomains_category_present(self):
        assert "subdomains" in self.present_categories

    def test_sensitive_dirs_category_present(self):
        assert "sensitive_dirs" in self.present_categories

    def test_emails_category_present(self):
        assert "emails" in self.present_categories

    def test_code_repos_category_present(self):
        assert "code_repos" in self.present_categories


# ---------------------------------------------------------------------------
# DorkGenerator — query content correctness
# ---------------------------------------------------------------------------

class TestDorkGeneratorQueryContent:
    def setup_method(self):
        self.gen = DorkGenerator()
        self.target = "example.com"
        self.result = self.gen.generate(self.target)

    def test_exposed_files_contains_pdf_dork(self):
        queries = self.result.by_category("exposed_files")
        pdf_queries = [q.query for q in queries if "pdf" in q.query]
        assert any(f"site:{self.target} filetype:pdf" == q for q in pdf_queries)

    def test_exposed_files_contains_sql_dork(self):
        queries = [q.query for q in self.result.by_category("exposed_files")]
        assert f"site:{self.target} filetype:sql" in queries

    def test_exposed_files_contains_env_dork(self):
        queries = [q.query for q in self.result.by_category("exposed_files")]
        assert f"site:{self.target} filetype:env" in queries

    def test_login_pages_contains_admin_dork(self):
        queries = [q.query for q in self.result.by_category("login_pages")]
        assert f"site:{self.target} inurl:admin" in queries

    def test_login_pages_contains_login_dork(self):
        queries = [q.query for q in self.result.by_category("login_pages")]
        assert f"site:{self.target} inurl:login" in queries

    def test_tech_stack_contains_phpmyadmin_dork(self):
        queries = [q.query for q in self.result.by_category("tech_stack")]
        assert any("phpMyAdmin" in q for q in queries)

    def test_tech_stack_contains_wordpress_dork(self):
        queries = [q.query for q in self.result.by_category("tech_stack")]
        assert any("wp-admin" in q for q in queries)

    def test_subdomains_contains_wildcard_dork(self):
        queries = [q.query for q in self.result.by_category("subdomains")]
        assert f"site:*.{self.target}" in queries

    def test_sensitive_dirs_contains_git_dork(self):
        queries = [q.query for q in self.result.by_category("sensitive_dirs")]
        assert any(".git" in q for q in queries)

    def test_sensitive_dirs_contains_backup_dork(self):
        queries = [q.query for q in self.result.by_category("sensitive_dirs")]
        assert any("backup" in q for q in queries)

    def test_emails_contains_at_domain_dork(self):
        queries = [q.query for q in self.result.by_category("emails")]
        assert any(f"@{self.target}" in q for q in queries)

    def test_code_repos_contains_github_dork(self):
        queries = [q.query for q in self.result.by_category("code_repos")]
        assert any("github.com" in q for q in queries)

    def test_code_repos_contains_gitlab_dork(self):
        queries = [q.query for q in self.result.by_category("code_repos")]
        assert any("gitlab.com" in q for q in queries)

    def test_code_repos_contains_pastebin_dork(self):
        queries = [q.query for q in self.result.by_category("code_repos")]
        assert any("pastebin.com" in q for q in queries)

    def test_all_queries_contain_target_domain(self):
        """Every generated query should reference the target domain."""
        for dq in self.result.queries:
            assert self.target in dq.query, (
                f"Query '{dq.query}' in category '{dq.category}' does not reference target"
            )

    def test_all_queries_have_non_empty_description(self):
        for dq in self.result.queries:
            assert dq.description.strip(), f"Empty description for query: {dq.query}"


class TestDorkGeneratorDifferentTargets:
    def test_different_targets_produce_different_queries(self):
        gen = DorkGenerator()
        r1 = gen.generate("foo.com")
        r2 = gen.generate("bar.org")
        assert r1.all_queries() != r2.all_queries()

    def test_target_preserved_in_result(self):
        gen = DorkGenerator()
        result = gen.generate("mysite.io")
        assert result.target == "mysite.io"

    def test_generate_is_deterministic(self):
        gen = DorkGenerator()
        r1 = gen.generate("example.com")
        r2 = gen.generate("example.com")
        assert r1.all_queries() == r2.all_queries()

    def test_generate_with_subdomain_target(self):
        gen = DorkGenerator()
        result = gen.generate("sub.example.com")
        assert result.target == "sub.example.com"
        assert all("sub.example.com" in q.query for q in result.queries)
