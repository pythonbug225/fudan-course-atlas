"""Export this batch's existing capture cache, offline; never contacts a service.

Usage: python export_raw.py --workspace PATH_TO_ORIGINAL_WORKSPACE
The shared sanitizer lives in scripts/research/build_raw_archive.py.
"""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

BATCH = Path(__file__).resolve().parent
REPO = BATCH.parents[3]
SPEC = importlib.util.spec_from_file_location(
    "snapshot_sanitizer", REPO / "scripts/research/build_raw_archive.py"
)
SAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAN)
DROP_FIELDS = {
    "history", "original", "extra", "achievements", "alter_by", "mention",
    "is_me", "liked", "disliked", "vote",
}
BODY_FIELDS = SAN.BODY_FIELDS | {"highlighted_content"}


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def posts(value):
    """Include nested reply snapshots; do not silently leak their text."""
    if isinstance(value, list):
        for item in value:
            yield from posts(item)
    elif isinstance(value, dict):
        if "content" in value and isinstance(value.get("id"), int):
            if "floor_id" in value or "ranking" in value:
                yield "floor", value
            elif "rank" in value:
                yield "review", value
        for key, item in value.items():
            if key not in DROP_FIELDS:
                yield from posts(item)


def restriction(post):
    if post.get("deleted") or post.get("time_deleted"):
        return "original_deleted"
    if post.get("fold") or post.get("fold_v2"):
        return "folded_content"
    if post.get("is_sensitive") or post.get("is_actual_sensitive"):
        return "sensitive_content"
    text = "\n".join(str(post.get(key, "")) for key in BODY_FIELDS)
    if SAN.NO_REPRINT.search(text):
        return "author_restricts_republication"
    return None


def transform(value, approved_floors, read_reviews, restricted, changes, seen):
    if isinstance(value, list):
        return [transform(x, approved_floors, read_reviews, restricted, changes, seen) for x in value]
    if not isinstance(value, dict):
        return value
    kind = None
    if "content" in value and isinstance(value.get("id"), int):
        if "floor_id" in value or "ranking" in value:
            kind = "floor"
        elif "rank" in value:
            kind = "review"
    status = None
    if kind:
        ident = value["id"]
        reason = restricted.get((kind, ident)) or restriction(value)
        allowed = ident in (approved_floors if kind == "floor" else read_reviews)
        status = reason or ("read_course_evidence" if kind == "floor" else "read_review_including_exclusions")
        if not reason and not allowed:
            reason = "unreviewed_or_unselected_candidate"
            status = reason
        seen[kind + "_ids"].add(ident)
        seen[kind + ("_body_withheld_ids" if reason else "_body_retained_ids")].add(ident)
    out = {}
    for key, item in value.items():
        if key in DROP_FIELDS:
            changes["removed_account_state_or_revision_field"] += 1
            continue
        if kind and reason and key in BODY_FIELDS:
            out[key] = "[正文未公开：" + reason + "]"
            changes["withheld_body_field"] += 1
        else:
            out[key] = transform(item, approved_floors, read_reviews, restricted, changes, seen)
    if kind:
        out["public_body_status"] = status
        out["source_url"] = (
            "https://forum.fduhole.com/api/floors/" if kind == "floor"
            else "https://danke.fduhole.com/api/reviews/"
        ) + str(ident)
    return out


def source_files(workspace):
    cache = workspace / "work/law-research"
    # Only capture responses and query plans, never runner/session/browser files.
    for path in sorted((cache / "live").glob("*.json")):
        category = "treehole" if path.name.startswith("forum") else "danke"
        yield path, category, "live/" + path.name
    for path in sorted((cache / "live-jobs").glob("*.json")):
        yield path, "research-ledgers", "query-plans/" + path.name
    official = workspace / "outputs/法学院课程研究_2025秋-2026春/官方资料"
    for path in sorted((official / "原始接口").glob("*.json")):
        yield path, "official-programs-and-outlines", "official/programs/" + path.name
    for path in sorted((official / "课程清单/原始接口").glob("*.json")):
        yield path, "official-outlines", "official/timetables/" + path.name


def run(workspace):
    evidence = load(BATCH / "summaries/evidence.json")
    reading = load(BATCH / "ledgers/fulltext-reading-ids.json")
    approved = {int(x) for e in evidence for x in e.get("source_floor_ids", [])}
    read_reviews = set(reading["danke_review_ids"])
    assert len(approved) == 477 and approved <= set(reading["forum_floor_ids"])
    sources = list(source_files(workspace))
    assert len(sources) == 58, "Unexpected cache file set; inspect before exporting"
    # Honor restriction flags across different captured versions of the same post.
    restricted = {}
    for path, category, logical in sources:
        if category not in {"treehole", "danke"}:
            continue
        for kind, post in posts(load(path)):
            reason = restriction(post)
            if reason:
                restricted.setdefault((kind, post["id"]), reason)
    target = BATCH / "raw"
    target.mkdir(exist_ok=True)
    rows = []
    total_changes = collections.Counter()
    total_seen = collections.defaultdict(set)
    for path, category, logical in sources:
        original = path.read_bytes()
        value = json.loads(original.decode("utf-8-sig"))
        changes = collections.Counter()
        seen = collections.defaultdict(set)
        value = transform(value, approved, read_reviews, restricted, changes, seen)
        value = SAN.sanitize(value, changes, category)
        restored = encode(value)
        packed = gzip.compress(restored, compresslevel=9, mtime=0)
        stored_path = logical + ".gz"
        dest = target / stored_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(packed)
        rows.append({
            "source_path": logical, "category": category,
            "captured_bytes": len(original), "captured_sha256": digest(original),
            "stored_path": stored_path, "stored_bytes": len(packed), "stored_sha256": digest(packed),
            "restored_bytes": len(restored), "restored_sha256": digest(restored),
            "redactions": dict(+changes),
            "post_counts": {key: len(ids) for key, ids in sorted(seen.items())},
            "read_status": "Captured does not mean read or adopted; see reading and evidence ledgers.",
        })
        total_changes.update(changes)
        for key, ids in seen.items():
            total_seen[key].update(ids)
    source_links = [{
        "evidence_id": e["evidence_id"], "source_id": e["source_id"],
        "floor_ids": e.get("source_floor_ids", []), "hole_ids": e.get("source_hole_ids", []),
        "review_ids": e.get("source_review_ids", []), "source_urls": e["source_urls"],
        "mapping_status": e["mapping_status"], "confirmed_section_keys": [],
    } for e in evidence]
    (target / "evidence-source-links.json").write_bytes(encode(source_links))
    result = {
        "schema": "law-captured-source-responses/1", "capture_date": "2026-10-29",
        "publication_date": "2026-10-30", "file_count": len(rows), "files": rows,
        "unique_post_counts": {key: len(ids) for key, ids in sorted(total_seen.items())},
        "redactions": dict(+total_changes),
        "counts": {
            "forum_search_candidates": 88781, "forum_context_holes": 232, "forum_context_floors": 11460,
            "danke_search_groups": 1133, "danke_detail_groups": 153, "danke_detail_courses": 997,
            "active_queries_per_service": 1775, "superseded_forum_queries": 96,
            "official_program_detail_responses": 8, "official_program_list_responses": 1,
            "official_timetable_responses": 2,
        },
        "license_source": "https://danxi.fduhole.com/doc/community-user-agreement",
        "license_note": "Community text defaults to CC BY 4.0 where the author owns copyright and states no exception. Individual restrictions prevail. Supplied anonymous attribution and source URLs are retained; missing attribution is not invented. Official materials retain their own rights.",
        "transformations": [
            "Captured JSON structure, IDs, query associations, pagination and timestamps are preserved; content is not an AI summary.",
            "Forum body publication is limited to the 477 source floor IDs explicitly cited by the read course-evidence ledger, subject to restriction checks; other candidates retain metadata and links.",
            "Review bodies are limited to the 71 actually read review IDs, including excluded and duplicate experiences; these are not 71 valid target-section reviews.",
            "Deleted, folded, sensitive and author-restricted text is withheld across captured versions; revision bodies, account state, identity/contact and credential fields are removed.",
            "captured_sha256 identifies the local acquisition file; restored_sha256 identifies the public redacted JSON; neither is presented as a network-wire byte digest.",
            "Superseded tokenized forum searches are retained for audit, separate from active exact/observed-alias queries.",
            "No external-platform full-text captures or browser diagnostics are included. Xiaohongshu, Zhihu and WeChat site searches remain incomplete.",
        ],
        "official_word_originals": "../release-assets.json",
    }
    (target / "manifest.json").write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    print(json.dumps({"files": len(rows), "compressed_bytes": sum(row["stored_bytes"] for row in rows), "unique_post_counts": result["unique_post_counts"], "redactions": result["redactions"]}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    run(parser.parse_args().workspace.resolve())
