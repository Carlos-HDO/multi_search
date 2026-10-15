#!/usr/bin/env python3
"""Unit tests for multi_search (standard library only, no external deps).

Run with:  python3 -m unittest discover -s tests
"""

import http.client
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import multi_search as m  # noqa: E402


class BuildSearchesTest(unittest.TestCase):
    def test_url_encoding_and_template(self):
        engines = [("Google", "google", "https://example.com/s?q={q}")]
        result = m.build_searches("a b&c", engines)
        self.assertEqual(result, [("Google", "https://example.com/s?q=a+b%26c")])

    def test_template_is_not_evaluated_as_format_string(self):
        engines = [("X", "x", "https://example.com/{q.__class__}/{0}?q={q}")]
        result = m.build_searches("abc", engines)
        self.assertEqual(result, [("X", "https://example.com/{q.__class__}/{0}?q=abc")])

    def test_non_web_urls_never_reach_the_browser(self):
        engines = [
            ("Flag", "flag", "--renderer-cmd-prefix=/bin/sh {q}"),
            ("JS", "js", "javascript:alert({q})"),
            ("File", "file", "file:///etc/{q}"),
            ("Bare", "bare", "{q}"),
        ]
        with mock.patch("sys.stderr"):
            self.assertEqual(m.build_searches("--gpu-launcher", engines), [])


class SanitizeConfigTest(unittest.TestCase):
    def _cfg(self, **engine):
        base = {"name": "X", "key": "x", "url_template": "https://example.com/?q={q}", "category_tag": "web"}
        base.update(engine)
        return {"engines": [base], "categories": {"web": {"title": "Web", "icon": "🌐", "description": "", "engines": ["x", "ghost"]}}}

    def test_default_config_is_valid(self):
        cfg, errors = m.sanitize_config(m.get_default_config())
        self.assertEqual(errors, [])
        self.assertEqual(cfg, m.get_default_config())

    def test_valid_engine_kept_and_unknown_category_keys_dropped(self):
        cfg, errors = m.sanitize_config(self._cfg())
        self.assertEqual(errors, [])
        self.assertEqual(cfg["categories"]["web"]["engines"], ["x"])

    def test_malicious_entries_rejected(self):
        bad = [
            {"url_template": "--renderer-cmd-prefix=/bin/sh {q}"},
            {"url_template": "javascript:alert(1)//{q}"},
            {"url_template": "https://example.com/ --flag {q}"},
            {"url_template": "https://example.com/"},  # no {q}
            {"key": "x');alert(1)//"},
            {"key": "x\n"},
            {"category_tag": "web\" onmouseover=\"alert(1)"},
            {"name": ""},
            {"name": 123},
        ]
        for override in bad:
            with self.subTest(override=override):
                cfg, errors = m.sanitize_config(self._cfg(**override))
                self.assertEqual(cfg["engines"], [])
                self.assertTrue(errors)

    def test_bad_structure_raises(self):
        for payload in ([], {"engines": "x", "categories": 1}, {"engines": []}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                m.sanitize_config(payload)


class ConfigFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg_dir = Path(self.tmp.name) / "multi_search"
        self.patches = [
            mock.patch.object(m, "CONFIG_DIR", cfg_dir),
            mock.patch.object(m, "CONFIG_FILE", cfg_dir / "config.json"),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_config_file_is_owner_only(self):
        m.save_config(m.get_default_config())
        self.assertEqual(stat.S_IMODE(os.stat(m.CONFIG_FILE).st_mode), 0o600)

    def test_load_drops_malicious_engine_from_disk(self):
        cfg = m.get_default_config()
        cfg["engines"].append({"name": "evil", "key": "evil", "url_template": "--gpu-launcher=sh {q}", "category_tag": "web"})
        m.CONFIG_DIR.mkdir(parents=True)
        m.CONFIG_FILE.write_text(json.dumps(cfg), encoding="utf-8")
        with mock.patch("sys.stderr"):
            loaded = m.load_config()
        self.assertNotIn("evil", [e["key"] for e in loaded["engines"]])
        self.assertEqual(len(loaded["engines"]), len(m.DEFAULT_ENGINES))


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
        cls.tmp = tempfile.TemporaryDirectory()
        cfg_dir = Path(cls.tmp.name) / "multi_search"
        cls.patches = [
            mock.patch.object(m, "CONFIG_DIR", cfg_dir),
            mock.patch.object(m, "CONFIG_FILE", cfg_dir / "config.json"),
        ]
        for p in cls.patches:
            p.start()
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), m.MultiSearchRequestHandler)
        cls.port = cls.httpd.server_address[1]
        cls.host = f"localhost:{cls.port}"
        cls.origin = f"http://{cls.host}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        for p in cls.patches:
            p.stop()
        cls.tmp.cleanup()

    def setUp(self):
        # Never spawn a real browser: record what would have been dispatched.
        patcher = mock.patch.object(m, "dispatch_searches")
        self.dispatch = patcher.start()
        self.addCleanup(patcher.stop)

    def _raw(self, method, path, headers=None, body=None):
        """Send a request with full control over headers; returns (status, headers, body)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        headers = {"Host": self.host, **(headers or {})}
        data = body.encode("utf-8") if isinstance(body, str) else body
        if data is not None and "Content-Length" not in headers:
            headers["Content-Length"] = str(len(data))
        for k, v in headers.items():
            conn.putheader(k, v)
        conn.endheaders(data)
        resp = conn.getresponse()
        result = resp.status, dict(resp.getheaders()), resp.read().decode("utf-8")
        conn.close()
        return result

    def _post(self, path, payload, headers=None):
        body = payload if isinstance(payload, str) else json.dumps(payload)
        return self._raw("POST", path, {"Content-Type": "application/json", **(headers or {})}, body)

    def _wait_dispatch(self):
        for _ in range(50):
            if self.dispatch.called:
                return self.dispatch.call_args.kwargs
            time.sleep(0.02)
        self.fail("dispatch_searches was not called")

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

    # --- origin / fetch-metadata hardening ---------------------------------

    def test_same_origin_launch_is_accepted(self):
        status, _, _ = self._post("/api/launch", {"query": "x", "engines": ["google"], "browser": "firefox"},
                                  {"Origin": self.origin, "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(status, 200)
        self.assertEqual(self._wait_dispatch()["browser_str"], "firefox")

    def test_other_localhost_port_is_forbidden(self):
        for origin in ("http://localhost:3000", "http://127.0.0.1:8888", "null", f"https://{self.host}"):
            with self.subTest(origin=origin):
                status, _, _ = self._post("/api/launch", {"query": "x", "engines": ["google"]}, {"Origin": origin})
                self.assertEqual(status, 403)
        self.dispatch.assert_not_called()

    def test_cross_site_fetch_metadata_is_forbidden_on_api(self):
        for site in ("cross-site", "same-site"):
            with self.subTest(site=site):
                status, _, _ = self._raw("GET", "/api/config", {"Sec-Fetch-Site": site})
                self.assertEqual(status, 403)

    def test_post_requires_json_content_type(self):
        status, _, _ = self._raw("POST", "/api/launch", {"Content-Type": "text/plain"},
                                 json.dumps({"query": "x", "engines": ["google"]}))
        self.assertEqual(status, 415)
        self.dispatch.assert_not_called()

    def test_security_headers_on_every_response(self):
        for method, path, headers in (("GET", "/", {}), ("GET", "/api/config", {"Host": "attacker.com"})):
            with self.subTest(path=path):
                _, resp_headers, _ = self._raw(method, path, headers)
                self.assertEqual(resp_headers.get("X-Frame-Options"), "DENY")
                self.assertIn("frame-ancestors 'none'", resp_headers.get("Content-Security-Policy", ""))
                self.assertEqual(resp_headers.get("X-Content-Type-Options"), "nosniff")

    # --- config validation ---------------------------------------------------

    def test_config_with_browser_flag_template_is_rejected(self):
        cfg = m.get_default_config()
        cfg["engines"].append({"name": "evil", "key": "evil",
                               "url_template": "--renderer-cmd-prefix=/bin/touch /tmp/pwned {q}", "category_tag": "web"})
        status, _, body = self._post("/api/config", cfg)
        self.assertEqual(status, 400)
        self.assertIn("url_template", body)
        self.assertNotIn("evil", [e["key"] for e in m.load_config()["engines"]])

    def test_config_with_bad_structure_is_rejected(self):
        status, _, _ = self._post("/api/config", {"engines": "x", "categories": 1})
        self.assertEqual(status, 400)

    def test_valid_config_is_saved_without_extra_fields(self):
        cfg = m.get_default_config()
        cfg["installed_browsers"] = [{"name": "x"}]
        status, _, _ = self._post("/api/config", cfg)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(m.CONFIG_FILE.read_text(encoding="utf-8")), m.get_default_config())

    # --- launch payload validation -------------------------------------------

    def test_malformed_launch_payloads_get_400(self):
        cases = [
            "[]",
            "not json",
            {"query": 123, "engines": ["google"]},
            {"query": "x", "engines": "google"},
            {"query": "x", "engines": [["google"]]},
            {"query": "x", "engines": ["google"], "browser": ["firefox"]},
            {"query": "x", "engines": ["google"], "delay": "abc"},
            {"query": "x" * (m.MAX_QUERY_LEN + 1), "engines": ["google"]},
        ]
        for payload in cases:
            with self.subTest(payload=str(payload)[:40]):
                status, _, _ = self._post("/api/launch", payload)
                self.assertEqual(status, 400)
        for nonfinite in ("NaN", "Infinity"):
            with self.subTest(delay=nonfinite):
                status, _, _ = self._post("/api/launch", f'{{"query": "x", "engines": ["google"], "delay": {nonfinite}}}')
                self.assertEqual(status, 400)
        self.dispatch.assert_not_called()

    def test_bad_content_length(self):
        status, _, _ = self._raw("POST", "/api/launch", {"Content-Type": "application/json", "Content-Length": "abc"}, b"")
        self.assertEqual(status, 400)
        status, _, _ = self._raw("POST", "/api/launch",
                                 {"Content-Type": "application/json", "Content-Length": str(m.MAX_BODY_BYTES + 1)}, b"")
        self.assertEqual(status, 413)

    def test_duplicate_engines_are_deduplicated(self):
        status, _, body = self._post("/api/launch", {"query": "x", "engines": ["google"] * 500 + ["bing"], "browser": "firefox"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["engines_count"], 2)
        self.assertEqual([k for _, k, _ in self._wait_dispatch()["engines"]], ["google", "bing"])

    def test_delay_is_clamped(self):
        self._post("/api/launch", {"query": "x", "engines": ["google"], "browser": "firefox", "delay": 1e9})
        self.assertEqual(self._wait_dispatch()["delay"], m.MAX_TAB_DELAY)

    def test_slow_client_does_not_block_server(self):
        slow = socket.create_connection(("127.0.0.1", self.port))
        try:
            slow.sendall(b"GET / HTTP/1.1\r\nHost: " + self.host.encode() + b"\r\n")  # never finished
            status, _, _ = self._raw("GET", "/api/config")
            self.assertEqual(status, 200)
            # Finish the slow request and drain it so the server closes cleanly.
            slow.sendall(b"\r\n")
            slow.settimeout(5)
            while slow.recv(65536):
                pass
        finally:
            slow.close()


if __name__ == "__main__":
    unittest.main()
