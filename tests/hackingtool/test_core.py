import pytest
from hackingtool.core.config import Config
from hackingtool.core.utils import (
    Colors, color, is_valid_ip, is_valid_domain, format_table
)


class TestConfig:
    def test_default_timeout(self):
        cfg = Config()
        assert cfg.timeout == 5

    def test_default_max_threads(self):
        cfg = Config()
        assert cfg.max_threads == 100

    def test_custom_timeout(self):
        cfg = Config(timeout=10)
        assert cfg.timeout == 10

    def test_output_path_creates_filename(self):
        import tempfile, os
        cfg = Config(output_dir=tempfile.gettempdir())
        path = cfg.output_path("test.txt")
        assert path.endswith("test.txt")
        assert os.path.dirname(path) == tempfile.gettempdir()

    def test_user_agent_contains_hackingtool(self):
        cfg = Config()
        assert "HackingTool" in cfg.user_agent

    def test_verbose_default_false(self):
        cfg = Config()
        assert cfg.verbose is False


class TestColorUtils:
    def test_color_wraps_with_ansi(self):
        result = color("hello", Colors.GREEN)
        assert Colors.GREEN in result
        assert Colors.RESET in result
        assert "hello" in result

    def test_is_valid_ip_valid(self):
        assert is_valid_ip("192.168.1.1") is True
        assert is_valid_ip("8.8.8.8") is True
        assert is_valid_ip("0.0.0.0") is True

    def test_is_valid_ip_invalid(self):
        assert is_valid_ip("not.an.ip") is False
        assert is_valid_ip("999.999.999.999") is False
        assert is_valid_ip("") is False

    def test_is_valid_domain_valid(self):
        assert is_valid_domain("example.com") is True
        assert is_valid_domain("sub.example.com") is True
        assert is_valid_domain("my-domain.co.uk") is True

    def test_is_valid_domain_invalid(self):
        assert is_valid_domain("localhost") is False
        assert is_valid_domain("") is False

    def test_format_table_headers(self):
        rows = [("val1", "val2")]
        table = format_table(rows, ["Header1", "Header2"])
        assert "Header1" in table
        assert "Header2" in table
        assert "val1" in table
        assert "val2" in table

    def test_format_table_border_lines(self):
        rows = [("a", "b")]
        table = format_table(rows, ["X", "Y"])
        lines = table.split("\n")
        assert lines[0].startswith("+")
        assert lines[-1].startswith("+")

    def test_format_table_empty_rows(self):
        table = format_table([], ["Col1", "Col2"])
        assert "Col1" in table


class TestBanner:
    def test_banner_prints_without_error(self, capsys):
        from hackingtool.core.banner import print_banner
        print_banner()
        captured = capsys.readouterr()
        assert "HACKING" in captured.out or "TOOL" in captured.out or len(captured.out) > 0
