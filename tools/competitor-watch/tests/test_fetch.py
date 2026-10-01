import unittest

import helpers
from competitor_watch.fetch import Fetcher, RawResponse, TransportError, decode_body

URL = "https://site.example/apps/1/thing"
ROBOTS = "https://site.example/robots.txt"
OK = helpers.html_response(URL, "<p>hello</p>")


def fetcher(routes, **kw):
    t = helpers.FakeTransport(routes)
    sleeps = []
    kw.setdefault("respect_robots", False)
    return Fetcher("test-agent/1 (+https://e.test)", transport=t, sleep=sleeps.append, **kw), t, sleeps


class Basics(unittest.TestCase):
    def test_success(self):
        f, t, sleeps = fetcher({URL: OK})
        r = f.fetch(URL)
        self.assertTrue(r.ok)
        self.assertEqual((r.status, r.attempts, r.error, r.body), (200, 1, None, b"<p>hello</p>"))
        self.assertEqual(sleeps, [])

    def test_the_request_says_who_is_asking_and_refuses_compression(self):
        f, t, _ = fetcher({URL: OK})
        f.fetch(URL)
        headers = t.calls[0][1]
        self.assertEqual(headers["User-Agent"], "test-agent/1 (+https://e.test)")
        self.assertEqual(headers["Accept-Encoding"], "identity")

    def test_a_404_is_a_failure_and_is_not_retried(self):
        f, t, sleeps = fetcher({URL: RawResponse(404, {}, b"", URL)})
        r = f.fetch(URL)
        self.assertEqual((r.ok, r.status, r.error, r.attempts), (False, 404, "HTTP 404", 1))
        self.assertEqual((len(t.calls), sleeps), (1, []))

    def test_403_is_not_retried_either(self):
        f, t, _ = fetcher({URL: RawResponse(403, {}, b"", URL)})
        self.assertEqual(f.fetch(URL).error, "HTTP 403")
        self.assertEqual(len(t.calls), 1)


class Retries(unittest.TestCase):
    def test_a_503_is_retried_with_growing_waits_and_can_succeed(self):
        busy = RawResponse(503, {}, b"", URL)
        f, t, sleeps = fetcher({URL: [busy, busy, OK]})
        r = f.fetch(URL)
        self.assertTrue(r.ok)
        self.assertEqual((r.attempts, sleeps), (3, [2.0, 6.0]))

    def test_it_gives_up_after_the_configured_retries_and_says_why(self):
        f, t, sleeps = fetcher({URL: RawResponse(503, {}, b"", URL)}, retries=1)
        r = f.fetch(URL)
        self.assertEqual((r.ok, r.error, r.attempts, len(t.calls), sleeps), (False, "HTTP 503", 2, 2, [2.0]))

    def test_429_honours_retry_after_up_to_a_cap(self):
        limited = RawResponse(429, {"retry-after": "5"}, b"", URL)
        f, _, sleeps = fetcher({URL: [limited, OK]})
        self.assertTrue(f.fetch(URL).ok)
        self.assertEqual(sleeps, [5.0])
        greedy = RawResponse(429, {"retry-after": "3600"}, b"", URL)
        f, _, sleeps = fetcher({URL: [greedy, OK]})
        f.fetch(URL)
        self.assertEqual(sleeps, [30.0])

    def test_network_errors_are_retried_and_then_reported(self):
        f, _, sleeps = fetcher({URL: TransportError("timeout: timed out")})
        r = f.fetch(URL)
        self.assertEqual((r.ok, r.status, r.error, r.attempts), (False, None, "timeout: timed out", 3))
        self.assertEqual(len(sleeps), 2)


class Content(unittest.TestCase):
    def test_a_binary_content_type_is_refused(self):
        f, _, _ = fetcher({URL: RawResponse(200, {"content-type": "application/pdf"}, b"%PDF", URL)})
        self.assertIn("unexpected content type", f.fetch(URL).error)

    def test_a_truncated_response_is_a_failure_not_a_silent_partial_page(self):
        f, _, _ = fetcher({URL: RawResponse(200, {"content-type": "text/html"}, b"x" * 10, URL, truncated=True)}, max_bytes=10)
        self.assertIn("larger than 10 bytes", f.fetch(URL).error)

    def test_the_final_url_after_a_redirect_is_kept(self):
        f, _, _ = fetcher({URL: RawResponse(200, {"content-type": "text/html"}, b"<p>x</p>", "https://site.example/apps/1/renamed")})
        self.assertEqual(f.fetch(URL).final_url, "https://site.example/apps/1/renamed")

    def test_decoding(self):
        self.assertEqual(decode_body("café".encode("latin-1"), "text/html; charset=ISO-8859-1"), "café")
        self.assertEqual(decode_body('<meta charset="windows-1252">caf\xe9'.encode("latin-1"), "text/html"), '<meta charset="windows-1252">café')
        self.assertEqual(decode_body(b"caf\xc3\xa9", None), "café")
        self.assertEqual(decode_body(b"x\xff", "text/html; charset=nonsense"), "x�")


class Robots(unittest.TestCase):
    def test_a_disallowed_path_is_never_requested(self):
        f, t, _ = fetcher({ROBOTS: helpers.html_response(ROBOTS, helpers.fixture("robots_disallow.txt")), URL: OK}, respect_robots=True)
        r = f.fetch(URL)
        self.assertEqual((r.ok, r.error), (False, "blocked by robots.txt"))
        self.assertEqual([c[0] for c in t.calls], [ROBOTS], "the page itself was not requested")

    def test_an_allowed_path_is_fetched_and_robots_is_read_once_per_site(self):
        f, t, _ = fetcher({ROBOTS: helpers.html_response(ROBOTS, helpers.fixture("robots_allow.txt")), URL: OK, "https://site.example/other": OK}, respect_robots=True)
        self.assertTrue(f.fetch(URL).ok)
        self.assertTrue(f.fetch("https://site.example/other").ok)
        self.assertEqual([c[0] for c in t.calls].count(ROBOTS), 1)

    def test_no_robots_txt_means_everything_is_allowed(self):
        f, _, _ = fetcher({ROBOTS: RawResponse(404, {}, b"", ROBOTS), URL: OK}, respect_robots=True)
        self.assertTrue(f.fetch(URL).ok)

    def test_a_broken_robots_txt_means_do_not_fetch(self):
        f, t, _ = fetcher({ROBOTS: RawResponse(503, {}, b"", ROBOTS), URL: OK}, respect_robots=True)
        r = f.fetch(URL)
        self.assertFalse(r.ok)
        self.assertIn("robots.txt unavailable (HTTP 503)", r.error)
        self.assertEqual([c[0] for c in t.calls], [ROBOTS])

    def test_an_unreachable_robots_txt_means_do_not_fetch(self):
        f, _, _ = fetcher({ROBOTS: TransportError("dns: no such host")}, respect_robots=True)
        self.assertIn("robots.txt unreachable", f.fetch(URL).error)

    def test_robots_can_be_switched_off_on_purpose(self):
        f, t, _ = fetcher({URL: OK}, respect_robots=False)
        self.assertTrue(f.fetch(URL).ok)
        self.assertEqual([c[0] for c in t.calls], [URL])


if __name__ == "__main__":
    unittest.main()
