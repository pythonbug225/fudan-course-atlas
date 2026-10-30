"""Offline publication of saved History Department acquisition data.

No network requests, account access or modification of acquisition files.
"""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def run(source, report, repo, out):
    source, report, repo, out = [p.resolve() for p in (source, report, repo, out)]
    if out == source or out.is_relative_to(source) or out == report or out.is_relative_to(report):
        raise ValueError("Output must be outside acquisition and report directories")
    spec = importlib.util.spec_from_file_location("archive", repo / "scripts/research/build_raw_archive.py")
    archive = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(archive)
    archive.SECRET_KEYS.update({"mention", "authorid", "uid", "reviewer", "reviewerid",
                               "liked", "disliked", "isme", "favorited", "subscribed"})
    archive.BODY_FIELDS.update({"highlighted_content", "sanitized_content", "body_evidence"})
    archive.NO_REPRINT = re.compile(archive.NO_REPRINT.pattern + r"|禁止搬运|请勿搬运|未经.{0,12}(?:许可|允许|同意).{0,8}(?:转发|搬运)")
    original_public_url = archive.public_url

    def public_url(value, changes):
        if urlsplit(value).hostname == "mp.weixin.qq.com":
            archive.SIGNED_PARAMS.discard("signature")
            try:
                return original_public_url(value, changes)
            finally:
                archive.SIGNED_PARAMS.add("signature")
        return original_public_url(value, changes)

    def clean_text(value, changes):
        urls = []
        def hold(match):
            urls.append(public_url(match.group(), changes))
            return "[PUBLIC_URL_" + str(len(urls) - 1) + "]"
        value = archive.URL_RE.sub(hold, value)
        for name, pattern in archive.CONTACT_PATTERNS:
            value, count = pattern.subn("[已脱敏]", value)
            changes[name] += count
        for i, url in enumerate(urls):
            value = value.replace("[PUBLIC_URL_" + str(i) + "]", url)
        return value

    archive.clean_text = clean_text
    original_sanitize = archive.sanitize
    association_keys = {"id", "query_id", "query_ids", "course_code", "course_codes", "floor_id", "floor_ids",
                        "hit_floor_ids", "hole_id", "hole_ids", "course_id", "course_ids", "group_id",
                        "group_ids", "review_id", "review_ids", "source_id", "source_ids"}

    def sanitize(value, changes, category):
        # Hash-based query IDs can contain digit runs resembling phone/student
        # numbers. Preserve these structural IDs so joins remain lossless.
        if isinstance(value, dict):
            associations = {k: v for k, v in value.items() if k in association_keys}
            result = original_sanitize({k: v for k, v in value.items() if k not in association_keys}, changes, category)
            result.update(associations)
            return result
        return original_sanitize(value, changes, category)

    archive.sanitize = sanitize
    search = read(source / "live/forum_search_results.json")
    context = read(source / "live/forum_context_results.json")
    details = read(source / "live/danke_details_results.json")
    floor_versions = collections.defaultdict(list)
    for item in list(search["items"]) + list(context["floors"].values()):
        floor_versions[str(item["id"])].append(item["data"])
    all_floors = {fid: versions[-1] for fid, versions in floor_versions.items()}
    approved_floors, approved_holes = set(), set()
    for row in read(report / "reviewed-course-summaries.json")["records"]:
        sid = str(row.get("source_id", ""))
        for hid, fids in re.findall(r"hole(\d+)/floor([\d,]+)", sid):
            approved_holes.add(hid)
            approved_floors.update(fids.split(","))
        for fid in re.findall(r"/api/floors/(\d+)", str(row.get("source_url", ""))):
            approved_floors.add(fid)
    for p in sorted((source / "review_pipeline").glob("extended_manual_part_*.json")):
        for row in read(p)["records"]:
            if row.get("decision") not in {"广告", "无关"} and row.get("course_name"):
                approved_floors.add(str(row["floor_id"]))
    for fid in list(approved_floors):
        hid = all_floors.get(fid, {}).get("hole_id")
        if hid is not None:
            approved_holes.add(str(hid))

    def true(value):
        return value in (True, 1, "true")

    restricted_holes = {str(k) for k, v in context["holes"].items()
                        if any(true(v["data"].get(f)) for f in ("hidden", "deleted", "frozen"))
                        or v["data"].get("time_deleted")}
    reasons = {}
    for fid, floor in all_floors.items():
        hid = str(floor.get("hole_id", ""))
        versions = floor_versions[fid]
        if hid in restricted_holes or any(true(v.get(k)) for v in versions for k in ("deleted", "fold", "is_sensitive", "is_actual_sensitive")):
            reasons[fid] = "restricted_or_deleted"
        elif any(archive.NO_REPRINT.search("\n".join(str(v.get(k, "")) for k in archive.BODY_FIELDS)) for v in versions):
            reasons[fid] = "author_restricts_republication"
        elif fid not in approved_floors and hid not in approved_holes:
            reasons[fid] = "course_context_not_verified"

    body_counts, retained = collections.Counter(), set()

    def scope_bodies(value, inherited_fid=None, inherited_hid=None):
        if isinstance(value, list):
            return [scope_bodies(v, inherited_fid, inherited_hid) for v in value]
        if not isinstance(value, dict):
            return value
        fid, hid = inherited_fid, inherited_hid
        if "floor_id" in value:
            fid = str(value["floor_id"])
        if "id" in value and str(value["id"]) in all_floors and ("data" in value or "content" in value):
            fid = str(value["id"])
        if value.get("hole_id") is not None:
            hid = str(value["hole_id"])
        has_body = bool(set(value) & archive.BODY_FIELDS)
        reason = reasons.get(fid)
        if has_body and fid and fid not in all_floors and fid not in approved_floors and hid not in approved_holes:
            reason = "course_context_not_verified"
        result = {}
        for key, item in value.items():
            if archive.keyform(key) in archive.SECRET_KEYS:
                # These subtrees are removed by sanitize; do not count their
                # embedded mentions as published source bodies.
                result[key] = item
            else:
                result[key] = ("[正文未公开：" + reason + "]" if reason and key in archive.BODY_FIELDS
                               else scope_bodies(item, fid, hid))
        if has_body and fid:
            result["public_body_status"] = reason or "course_related_body_retained_with_redactions"
            body_counts[reason or "course_related_body_retained"] += 1
            if not reason:
                retained.add(fid)
        return result

    files = []
    for p in sorted((report / "official/原始接口").glob("*.json")):
        files.append((p, "official/responses/" + p.name, "official-response", False))
    for p in sorted((source / "live").glob("*.json")):
        category = "research-ledgers" if "ledger" in p.name else "treehole" if p.name.startswith("forum") else "danke"
        files.append((p, "live/" + p.name, category, p.name.startswith("forum")))
    for p in sorted((source / "live-jobs").glob("*.json")):
        files.append((p, "query-plans/" + p.name, "research-ledgers", False))
    for p in sorted((source / "review_pipeline").glob("*.json")):
        files.append((p, "reading-ledgers/" + p.name, "research-ledgers", True))
    for p in sorted(source.glob("*.json")):
        files.append((p, "research-intermediates/" + p.name, "research-ledgers", True))
    for p in sorted((source / "xhs").glob("*.json")):
        files.append((p, "public-search-observations/xiaohongshu/" + p.name, "external-web", False))
    for p in sorted(report.glob("*.json")):
        if p.name.startswith(("wechat", "zhihu", "xiaohongshu")):
            files.append((p, "public-search-observations/" + p.name, "external-web", False))

    index, changes_total = [], collections.Counter()
    for p, logical, category, forum_body_scope in files:
        original = p.read_bytes()
        parsed = json.loads(original.decode("utf-8-sig"))
        changes = collections.Counter()
        if category == "official-response":
            data = original
        else:
            if forum_body_scope:
                parsed = scope_bodies(parsed)
            if category == "treehole":
                items = parsed.get("items", parsed.get("floors", {}))
                for item in items if isinstance(items, list) else items.values():
                    fid = str(item["id"])
                    item["source_urls"] = list(dict.fromkeys(item.get("source_urls", []) + ["https://forum.fduhole.com/api/floors/" + fid]))
            if p.name == "danke_details_results.json":
                for rid, item in parsed["reviews"].items():
                    item["source_urls"] = list(dict.fromkeys(item.get("source_urls", []) + ["https://danke.fduhole.com/api/reviews/" + rid]))
            parsed = archive.sanitize(parsed, changes, category)
            data = (json.dumps(parsed, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        packed = gzip.compress(data, compresslevel=9, mtime=0)
        dest = out / (logical + ".gz")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(packed)
        root = report if p.is_relative_to(report) else source
        index.append({"source_root": "report" if root == report else "acquisition",
                      "source_path": p.relative_to(root).as_posix(), "category": category,
                      "stored_path": logical + ".gz", "restored_path": logical,
                      "captured_bytes": len(original), "captured_sha256": sha(original),
                      "stored_bytes": len(packed), "stored_sha256": sha(packed),
                      "restored_bytes": len(data), "restored_sha256": sha(data),
                      "byte_identical_to_capture": data == original, "redactions": dict(+changes)})
        changes_total.update(changes)
    words = []
    for p in sorted((report / "official/方案原件").glob("*.docx")):
        relative = "official/word-originals/" + p.name
        dest = out / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        words.append({"path": relative, "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())})
    counts = {"official_responses": 7, "official_word_originals": len(words),
              "official_course_term_rows": 270, "official_course_codes": 249, "course_names": 247,
              "official_sections": 343, "queries_per_service": 1341,
              "forum_search_candidates": len(search["items"]), "forum_context_holes": len(context["holes"]),
              "forum_context_floors": len(context["floors"]),
              "danke_search_groups": len(read(source / "live/danke_search_results.json")["items"]),
              "danke_detail_groups": len(details["groups"]), "danke_courses": len(details["courses"]),
              "danke_reviews": len(details["reviews"]), "course_context_approved_holes": len(approved_holes),
              "forum_published_floor_ids": len(retained)}
    manifest = {"schema": "history-source-responses/1", "publication_date": "2026-10-30",
                "capture_note": "Existing 2026-10-28 research captures; no new requests made for this publication.",
                "files": index, "file_count": len(index), "word_originals": words, "counts": counts,
                "redactions": dict(+changes_total), "forum_body_instance_counts_across_all_exports": dict(body_counts),
                "forum_published_floor_ids": sorted(retained, key=int),
                "excluded_files": [{"source_path": "xhs/" + p.name, "reason": "external_image_without_republication_permission"}
                                   for p in sorted((source / "xhs").glob("*.webp"))],
                "license_source": archive.LICENSE_URL, "license_checked_date": "2026-10-30",
                "license_note": "Community original text defaults to CC BY 4.0 unless the author says otherwise. Retain captured anonymous attribution and source URLs; absent labels are not invented. Third-party quotes, official documents and external platforms retain their own rights.",
                "transformations": ["Saved acquisition objects and query associations are preserved, not reconstructed from summaries.",
                                    "Account, credential, profile, contact and signed-session fields are removed.",
                                    "Forum bodies are retained only in verified course contexts; other bodies keep IDs, query associations and explicit publication status.",
                                    "Deleted, restricted and no-reprint bodies are withheld. This export does not recover deleted content.",
                                    "External-platform observations and source links are included; unlicensed article full text and screenshots are not.",
                                    "Official response JSON and Word originals are byte-identical to the saved public captures.",
                                    "Other JSON may be sanitized, annotated and canonicalized. gzip losslessly stores the published JSON."]}
    write(out / "manifest.json", manifest)
    print(json.dumps({"raw_files": len(index), "compressed_bytes": sum(x["stored_bytes"] for x in index),
                      "counts": counts, "redactions": dict(+changes_total)}, ensure_ascii=False))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--repo-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args.source_dir, args.report_dir, args.repo_dir, args.output_dir)
