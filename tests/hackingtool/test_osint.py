import pytest
from unittest.mock import patch
from hackingtool.modules.osint.ip_lookup import IPLookup, IPInfo, _is_bogon, _ip_to_int
from hackingtool.core.config import Config


class TestBogonDetection:
    def test_private_10_is_bogon(self):
        assert _is_bogon("10.0.0.1") is True

    def test_private_192_168_is_bogon(self):
        assert _is_bogon("192.168.1.1") is True

    def test_loopback_is_bogon(self):
        assert _is_bogon("127.0.0.1") is True

    def test_public_ip_is_not_bogon(self):
        assert _is_bogon("8.8.8.8") is False

    def test_172_16_range_is_bogon(self):
        assert _is_bogon("172.16.0.1") is True
        assert _is_bogon("172.31.255.255") is True

    def test_172_32_is_not_bogon(self):
        assert _is_bogon("172.32.0.1") is False


class TestIPToInt:
    def test_loopback(self):
        assert _ip_to_int("127.0.0.1") == (127 << 24) | 1

    def test_broadcast(self):
        assert _ip_to_int("255.255.255.255") == 0xFFFFFFFF

    def test_zero(self):
        assert _ip_to_int("0.0.0.0") == 0


class TestIPInfo:
    def test_success_true_when_no_error(self):
        info = IPInfo(ip="8.8.8.8")
        assert info.success is True

    def test_success_false_when_error(self):
        info = IPInfo(ip="8.8.8.8", error="Lookup failed")
        assert info.success is False

    def test_coordinates_when_both_set(self):
        info = IPInfo(ip="8.8.8.8", latitude=37.751, longitude=-97.822)
        assert info.coordinates == "37.751,-97.822"

    def test_coordinates_none_when_missing(self):
        info = IPInfo(ip="8.8.8.8")
        assert info.coordinates is None


class TestIPLookup:
    def setup_method(self):
        self.lookup = IPLookup(Config(timeout=3))

    def test_is_ip_returns_true_for_valid_ip(self):
        assert self.lookup._is_ip("8.8.8.8") is True

    def test_is_ip_returns_false_for_hostname(self):
        assert self.lookup._is_ip("example.com") is False

    def test_bogon_ip_returns_without_api_call(self):
        info = self.lookup.lookup("192.168.1.1")
        assert info.is_bogon is True
        assert info.success is True
        assert info.city is None

    def test_lookup_valid_ip_calls_api(self):
        mock_response_data = {
            "status": "success",
            "country": "United States",
            "countryCode": "US",
            "city": "Mountain View",
            "regionName": "California",
            "org": "AS15169 Google LLC",
            "isp": "Google LLC",
            "lat": 37.386,
            "lon": -122.084,
            "timezone": "America/Los_Angeles",
            "query": "8.8.8.8",
            "reverse": "dns.google",
        }
        import json
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(mock_response_data).encode()

        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = self.lookup.lookup("8.8.8.8")

        assert info.success is True
        assert info.country == "United States"
        assert info.city == "Mountain View"
        assert info.latitude == 37.386

    def test_lookup_handles_api_failure(self):
        mock_response_data = {"status": "fail", "message": "invalid query"}
        import json
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(mock_response_data).encode()

        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = self.lookup.lookup("8.8.8.8")

        assert info.success is False

    def test_lookup_handles_network_error(self):
        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            info = self.lookup.lookup("8.8.8.8")
        assert info.success is False

    def test_resolve_returns_none_for_invalid_host(self):
        import socket as _socket
        with patch("hackingtool.modules.osint.ip_lookup.socket.gethostbyname",
                   side_effect=_socket.gaierror("DNS fail")):
            result = self.lookup._resolve("invalid.invalid.invalid")
        assert result is None
