"""Privacy boundaries and restoration integrity for this raw-data publication."""
import collections
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import export_raw as export
import restore_raw as restore


def clean(value, floors=None, reviews=None, restricted=None):
    changes = collections.Counter()
    seen = collections.defaultdict(set)
    result = export.transform(value, floors or set(), reviews or set(), restricted or {}, changes, seen)
    return export.SAN.sanitize(result, changes, "treehole"), changes


class RawTests(unittest.TestCase):
    def test_preserves_course_source_but_withholds_unselected_nested_reply(self):
        value = {"id": 10, "floor_id": 0, "content": "课程原文", "anonyname": "匿名松鼠",
                 "reply_to": {"id": 11, "floor_id": 1, "content": "UNSELECTED_PRIVATE_TEXT"},
                 "query_ids": ["QUERY-1"], "course_codes": ["LAW10004"]}
        result, _ = clean(value, floors={10})
        self.assertEqual(result["content"], "课程原文")
        self.assertEqual(result["anonyname"], "匿名松鼠")
        self.assertEqual(result["query_ids"], value["query_ids"])
        self.assertEqual(result["course_codes"], value["course_codes"])
        self.assertNotIn("UNSELECTED_PRIVATE_TEXT", json.dumps(result))
        self.assertEqual(result["source_url"], "https://forum.fduhole.com/api/floors/10")

    def test_cross_snapshot_restrictions_win_over_allowlist(self):
        value = {"id": 10, "floor_id": 0, "content": "OLD_DELETED_BODY", "deleted": False}
        result, _ = clean(value, floors={10}, restricted={("floor", 10): "original_deleted"})
        self.assertNotIn("OLD_DELETED_BODY", json.dumps(result))
        self.assertEqual(result["public_body_status"], "original_deleted")

    def test_account_revisions_and_contacts_removed_without_altering_grades(self):
        value = {"id": 50, "rank": {"overall": 4}, "content": {"content": "原文 user@example.com"},
                 "history": [{"original": "OLD_PRIVATE_TEXT"}], "is_me": True, "mention": [123],
                 "user_id": 123, "access_token": "FAKE_SECRET", "year": 2024, "semester": "S3"}
        result, _ = clean(value, reviews={50})
        text = json.dumps(result)
        for forbidden in ["OLD_PRIVATE_TEXT", "user@example.com", "FAKE_SECRET"]:
            self.assertNotIn(forbidden, text)
        self.assertEqual(result["rank"], {"overall": 4})
        self.assertEqual((result["year"], result["semester"]), (2024, "S3"))
        for key in ["history", "is_me", "mention", "user_id", "access_token"]:
            self.assertNotIn(key, result)

    def test_opt_out_and_folded_text_withheld(self):
        for extra in [{"content": "禁止转载 BODY"}, {"fold_v2": "谨慎点开"}, {"is_sensitive": True}]:
            value = {"id": 10, "floor_id": 0, "content": "BODY", **extra}
            result, _ = clean(value, floors={10})
            self.assertNotIn("BODY", result["content"])

    def test_restore_rejects_traversal_and_existing_different_data(self):
        for path in ["../escape.json", "/escape.json", "C:/escape.json", "dir\\escape.json"]:
            with self.assertRaises(ValueError):
                restore.safe_path(Path("destination"), path)
        with tempfile.TemporaryDirectory() as temp:
            row = json.loads((restore.BATCH / "raw/manifest.json").read_text("utf8"))["files"][0]
            dest = restore.safe_path(Path(temp), row["source_path"])
            dest.parent.mkdir(parents=True)
            dest.write_text("RESEARCHER_DATA", encoding="utf8")
            with self.assertRaises(FileExistsError):
                restore.verify(Path(temp))
            self.assertEqual(dest.read_text("utf8"), "RESEARCHER_DATA")

    def test_published_responses_preserve_counts_and_evidence_bodies(self):
        root = restore.BATCH / "raw"
        def raw(name):
            return json.loads(gzip.decompress((root / name).read_bytes()))
        searches = raw("live/forum_search_results.json.gz")
        contexts = raw("live/forum_context_results.json.gz")
        reviews = {}
        floors = {}
        for path in (root / "live").glob("*.json.gz"):
            for kind, post in export.posts(json.loads(gzip.decompress(path.read_bytes()))):
                (floors if kind == "floor" else reviews).setdefault(post["id"], []).append(post)
        evidence = json.loads((restore.BATCH / "summaries/evidence.json").read_text("utf8"))
        approved = {int(x) for e in evidence for x in e.get("source_floor_ids", [])}
        reading = json.loads((restore.BATCH / "ledgers/fulltext-reading-ids.json").read_text("utf8"))
        self.assertEqual(len(searches["items"]), 88781)
        self.assertEqual(len(contexts["holes"]), 232)
        self.assertEqual(len(contexts["floors"]), 11460)
        self.assertTrue(approved <= floors.keys())
        self.assertTrue(set(reading["danke_review_ids"]) <= reviews.keys())
        for kind, table, allowed in [("floor", floors, approved), ("review", reviews, set(reading["danke_review_ids"]))]:
            for ident, versions in table.items():
                for post in versions:
                    if post["public_body_status"].startswith("read_"):
                        self.assertIn(ident, allowed)
                    else:
                        self.assertTrue(str(post["content"]).startswith("[正文未公开："))
        for term, count in [("2025秋", 174), ("2026春", 195)]:
            self.assertEqual(len(raw("official/timetables/" + term + "法学院教学班.json.gz")["data"]), count)

    def test_all_published_captures_exclude_credential_and_identity_fields(self):
        def inspect(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertNotIn(export.SAN.keyform(key), export.SAN.SECRET_KEYS)
                    self.assertNotIn(key, export.DROP_FIELDS)
                    inspect(item)
            elif isinstance(value, list):
                for item in value:
                    inspect(item)
            elif isinstance(value, str):
                for name, pattern in export.SAN.CONTACT_PATTERNS:
                    self.assertIsNone(pattern.search(value), name)
        for path in (restore.BATCH / "raw").rglob("*.json.gz"):
            inspect(json.loads(gzip.decompress(path.read_bytes())))


if __name__ == "__main__":
    unittest.main()
