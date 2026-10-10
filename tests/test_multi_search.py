#!/usr/bin/env python3
"""Unit tests for multi_search (standard library only, no external deps).

Run with:  python3 -m unittest discover -s tests
"""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import multi_search as m  # noqa: E402


class BuildSearchesTest(unittest.TestCase):
    def test_url_encoding_and_template(self):
        engines = [("Google", "google", "https://example.com/s?q={q}")]
        result = m.build_searches("a b&c", engines)
        self.assertEqual(result, [("Google", "https://example.com/s?q=a+b%26c")])


class CalculateDelayTest(unittest.TestCase):
    def test_no_jitter_returns_base_floor(self):
        self.assertEqual(m.calculate_delay(1.5, 0.0), 1.5)
        # base is floored at 0.05 when non-positive
        self.assertEqual(m.calculate_delay(0.0, 0.0), 0.05)

    def test_jitter_stays_within_bounds(self):
        for _ in range(200):
            val = m.calculate_delay(1.8, 0.8)
            self.assertGreaterEqual(val, 1.0)
            self.assertLessEqual(val, 2.6)


class FilterEnginesTest(unittest.TestCase):
    def setUp(self):
        self.cfg = m.get_default_config()

    def test_alias_resolution(self):
        res = m.filter_engines(["vt,gh"], self.cfg)
        keys = {k for _, k, _ in res}
        self.assertEqual(keys, {"virustotal", "github"})

    def test_comma_and_whitespace(self):
        res = m.filter_engines([" shodan , urlscan "], self.cfg)
        keys = {k for _, k, _ in res}
        self.assertEqual(keys, {"shodan", "urlscan"})


class CategoryTest(unittest.TestCase):
    def test_web_category_has_seven_engines(self):
        cfg = m.get_default_config()
        res = m.get_engines_by_category("web", cfg)
        self.assertEqual(len(res), 7)


class ValidateBrowserTest(unittest.TestCase):
    """The HTTP-facing browser validator must never pass through arbitrary commands."""

    def test_empty_falls_back_to_default(self):
        self.assertTrue(m.validate_requested_browser(""))
        self.assertTrue(m.validate_requested_browser(None))

    def test_known_alias_accepted(self):
        # 'firefox' is a known alias regardless of what is installed.
        self.assertEqual(m.validate_requested_browser("firefox"), "firefox")
        self.assertEqual(m.validate_requested_browser("FireFox"), "firefox")

    def test_arbitrary_command_rejected(self):
        self.assertIsNone(m.validate_requested_browser("sh -c 'id'"))
        self.assertIsNone(m.validate_requested_browser("/bin/bash"))
        self.assertIsNone(m.validate_requested_browser("rm -rf /"))
        self.assertIsNone(m.validate_requested_browser("totally-unknown-binary"))


class ServerSecurityTest(unittest.TestCase):
    """Integration tests that lock in the cross-origin / command-exec hardening.

    Only rejection paths (403/400) and a plain GET are exercised, so no real
    browser is ever spawned.
    """

    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), m.MultiSearchRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.host = f"localhost:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(self, path, method="GET", headers=None, body=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = body.encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Host", (headers or {}).get("Host", self.host))
        for k, v in (headers or {}).items():
            if k != "Host":
                req.add_header(k, v)
        try:
            resp = urllib.request.urlopen(req, timeout=5)
            return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_same_origin_get_serves_injected_catalog(self):
        status, body = self._request("/", headers={"Origin": f"http://{self.host}"})
        self.assertEqual(status, 200)
        self.assertIn("__MSEARCH_DEFAULTS__", body)

    def test_cross_origin_post_is_forbidden(self):
        status, _ = self._request(
            "/api/launch",
            method="POST",
            headers={"Origin": "https://evil.example", "Content-Type": "application/json"},
            body=json.dumps({"query": "x", "engines": ["google"]}),
        )
        self.assertEqual(status, 403)

    def test_foreign_host_is_forbidden(self):
        status, _ = self._request("/api/config", headers={"Host": "attacker.com"})
        self.assertEqual(status, 403)

    def test_unknown_browser_is_rejected(self):
        status, body = self._request(
            "/api/launch",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"query": "x", "engines": ["google"], "browser": "sh -c 'id'"}),
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
