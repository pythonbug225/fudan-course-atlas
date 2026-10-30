"""Fixture-only tests; these never call either live API."""
import urllib.parse
import unittest

from luna_readonly_client import ApiError, DankeClient, TreeholeClient


def floor_fixture(identifier):
    return {"id": identifier, "hole_id": 501, "content": f"fixture-floor-{identifier}"}


def course_group_fixture(identifier):
    return {"id": identifier, "name": f"fixture-course-{identifier}", "code": f"FIX{identifier}"}


class FixtureTransport:
    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append({"url": url, "headers": dict(headers), "timeout": timeout})
        return self.responder(url, headers, timeout)


class ReadOnlyClientTests(unittest.TestCase):
    def test_treehole_offset_pages_are_deduped_and_stop_on_empty_page(self):
        def respond(url, _headers, _timeout):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            offset = int(params["offset"][0])
            return {
                0: [floor_fixture(1), floor_fixture(2)],
                2: [floor_fixture(2), floor_fixture(3)],
                4: [],
            }[offset]

        transport = FixtureTransport(respond)
        client = TreeholeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")
        result = client.search_floors("fixture query", page_size=2, max_pages=5, accurate=True)

        self.assertEqual([row["id"] for row in result["items"]], [1, 2, 3])
        self.assertEqual(result["pages_fetched"], 3)
        self.assertEqual(len(transport.calls), 3)
        first_params = urllib.parse.parse_qs(urllib.parse.urlparse(transport.calls[0]["url"]).query)
        self.assertEqual(first_params["accurate"], ["true"])

    def test_short_treehole_page_stops_without_extra_request(self):
        transport = FixtureTransport(lambda *_: [floor_fixture(10)])
        client = TreeholeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")
        result = client.search_floors("fixture", page_size=3, max_pages=4)
        self.assertEqual([row["id"] for row in result["items"]], [10])
        self.assertEqual(len(transport.calls), 1)

    def test_danke_pages_are_deduped_and_search_is_get_only(self):
        def respond(url, _headers, _timeout):
            params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            page = int(params["page"][0])
            data = {
                1: [course_group_fixture(1), course_group_fixture(2)],
                2: [course_group_fixture(2), course_group_fixture(3)],
                3: [],
            }[page]
            return {"items": data, "page": page, "page_size": 2, "extra": {}}

        transport = FixtureTransport(respond)
        client = DankeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "fixture-token")
        result = client.search_course_groups("fixture", page_size=2, max_pages=4)

        self.assertEqual([row["id"] for row in result["items"]], [1, 2, 3])
        self.assertEqual(len(transport.calls), 3)
        self.assertTrue(all(call["url"].startswith("https://danke.fduhole.com/api/") for call in transport.calls))
        self.assertTrue(all(call["headers"]["Authorization"] == "Bearer fixture-token" for call in transport.calls))

    def test_auth_error_records_safe_failure_context_and_stops_paging(self):
        transport = FixtureTransport(lambda *_: (_ for _ in ()).throw(ApiError("HTTP 401", kind="http", status=401)))
        client = TreeholeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "fixture-secret")
        result = client.search_floors("fixture", page_size=1, max_pages=3)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(result["failures"][0]["status"], 401)
        self.assertEqual(result["failures"][0]["context"]["offset"], 0)
        self.assertNotIn("fixture-secret", repr(result["failures"]))

    def test_zero_page_size_is_rejected_before_transport(self):
        transport = FixtureTransport(lambda *_: [])
        client = DankeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")
        with self.assertRaises(ValueError):
            client.search_course_groups("fixture", page_size=0)
        self.assertEqual(transport.calls, [])

    def test_detail_routes_are_fixed_and_id_validated(self):
        transport = FixtureTransport(lambda url, *_: {"request_url": url})
        treehole = TreeholeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")
        danke = DankeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")

        self.assertIn("/holes/7", treehole.get_hole(7)["request_url"])
        self.assertIn("/floors/8", treehole.get_floor(8)["request_url"])
        self.assertIn("/v3/course_groups/9", danke.get_course_group(9)["request_url"])
        self.assertIn("/reviews/10", danke.get_review(10)["request_url"])
        with self.assertRaises(ValueError):
            treehole.get_hole(0)

    def test_single_course_reviews_return_fixture_array(self):
        fixture = [{"id": 11, "title": "fixture review", "content": "synthetic"}]
        transport = FixtureTransport(lambda *_: fixture)
        client = DankeClient(transport=transport, min_interval_s=0, token_provider=lambda _name: "")
        self.assertEqual(client.list_course_reviews(20), fixture)
        self.assertIn("/courses/20/reviews", transport.calls[0]["url"])


if __name__ == "__main__":
    unittest.main()