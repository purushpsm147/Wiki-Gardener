"""The real urllib transport, against a throwaway HTTP server on localhost. No external network is touched."""
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import helpers
from competitor_watch.fetch import Fetcher

HTML = helpers.fixture("listing_text.html")
ROBOTS = "User-agent: *\nDisallow: /private/\n"


class Handler(BaseHTTPRequestHandler):
    hits: dict[str, int] = {}

    def log_message(self, *args):  # keep test output clean
        pass

    def reply(self, status, body=b"", ctype="text/html; charset=utf-8", headers=()):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        path = self.path
        Handler.hits[path] = Handler.hits.get(path, 0) + 1
        if path == "/ok":
            self.reply(200, HTML.encode())
        elif path == "/redirect":
            self.reply(301, b"", headers=[("Location", "/ok")])
        elif path == "/missing":
            self.reply(404, b"nope")
        elif path == "/flaky":
            self.reply(200, HTML.encode()) if Handler.hits[path] >= 3 else self.reply(503, b"busy", headers=[("Retry-After", "1")])
        elif path == "/slow":
            time.sleep(1.0)
            self.reply(200, HTML.encode())
        elif path == "/robots.txt":
            self.reply(200, ROBOTS.encode(), ctype="text/plain")
        elif path == "/private/page":
            self.reply(200, HTML.encode())
        elif path == "/big":
            self.reply(200, b"x" * 50_000)
        elif path == "/pdf":
            self.reply(200, b"%PDF-1.4", ctype="application/pdf")
        elif path == "/latin1":
            self.reply(200, "<p>café</p>".encode("latin-1"), ctype="text/html; charset=ISO-8859-1")
        else:
            self.reply(404)


class LocalTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        Handler.hits.clear()

    def fetcher(self, **kw):
        kw.setdefault("respect_robots", False)
        return Fetcher("test-agent/1 (+https://e.test)", sleep=lambda s: None, timeout=kw.pop("timeout", 5.0), **kw)

    def test_a_plain_page(self):
        r = self.fetcher().fetch(self.base + "/ok")
        self.assertEqual((r.ok, r.status, r.error, r.attempts), (True, 200, None, 1))
        self.assertEqual(r.body.decode(), HTML)
        self.assertIn("text/html", r.content_type)

    def test_a_redirect_is_followed_and_the_final_url_is_recorded(self):
        r = self.fetcher().fetch(self.base + "/redirect")
        self.assertTrue(r.ok)
        self.assertEqual(r.final_url, self.base + "/ok")

    def test_a_404_is_reported_with_its_status_and_not_retried(self):
        r = self.fetcher().fetch(self.base + "/missing")
        self.assertEqual((r.ok, r.status, r.error, Handler.hits["/missing"]), (False, 404, "HTTP 404", 1))

    def test_a_flaky_server_is_retried_until_it_answers(self):
        r = self.fetcher().fetch(self.base + "/flaky")
        self.assertEqual((r.ok, r.attempts, Handler.hits["/flaky"]), (True, 3, 3))

    def test_a_server_slower_than_the_timeout_is_a_reported_failure(self):
        r = self.fetcher(timeout=0.3, retries=0).fetch(self.base + "/slow")
        self.assertFalse(r.ok)
        self.assertIsNone(r.status)
        self.assertRegex(r.error, r"timed? ?out")

    def test_a_refused_connection_is_a_reported_failure(self):
        r = self.fetcher(retries=0).fetch("http://127.0.0.1:1/never")
        self.assertFalse(r.ok)
        self.assertIsNone(r.status)
        self.assertTrue(r.error)

    def test_robots_txt_is_fetched_for_real_and_a_disallowed_path_is_never_requested(self):
        f = self.fetcher(respect_robots=True)
        blocked = f.fetch(self.base + "/private/page")
        self.assertEqual((blocked.ok, blocked.error), (False, "blocked by robots.txt"))
        self.assertNotIn("/private/page", Handler.hits)
        self.assertTrue(f.fetch(self.base + "/ok").ok)
        self.assertEqual(Handler.hits["/robots.txt"], 1)

    def test_an_oversized_body_is_a_failure(self):
        r = self.fetcher(max_bytes=1000).fetch(self.base + "/big")
        self.assertFalse(r.ok)
        self.assertIn("larger than 1000 bytes", r.error)

    def test_a_non_text_content_type_is_refused(self):
        self.assertIn("unexpected content type", self.fetcher().fetch(self.base + "/pdf").error)

    def test_declared_charsets_are_honoured_end_to_end(self):
        from competitor_watch.fetch import decode_body

        r = self.fetcher().fetch(self.base + "/latin1")
        self.assertEqual(decode_body(r.body, r.content_type), "<p>café</p>")


if __name__ == "__main__":
    unittest.main()
