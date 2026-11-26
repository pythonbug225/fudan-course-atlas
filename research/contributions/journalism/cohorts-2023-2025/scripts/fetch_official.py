"""Fetch official Fudan Journalism School undergraduate study plans (2023-2025).

The script stores the original public directory/detail responses and the original
Word exports, then writes an audit manifest for each cohort. It requires no login.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import posixpath
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

WORK = Path(__file__).resolve().parent
OUT = WORK / "sources"
HOST = "https://fdjwgl.fudan.edu.cn"
BASE = HOST + "/manager/bizType/2"
DEPARTMENT_ID = 2621
DEPARTMENT_NAME = "新闻学院"
YEARS = (2023, 2024, 2025)
PAGE_SIZE = 100
MAX_PAGES = 30

# These specific degree names are useful for recording cross-department candidates.
# General/public/common curriculum rows are deliberately excluded from this rule.
RELATED_MAJOR_TERMS = ("新闻学", "传播学", "广播电视学", "广告学")
GENERIC_TERMS = ("公共培养", "通识", "全校", "公共课", "新闻传播学类")


def json_bytes(data) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(data))


def request(url: str, data: bytes | None = None) -> tuple[bytes, str]:
    for attempt in range(3):
        try:
            headers = {"User-Agent": "Fudan-News-Curriculum-Research/1.0"}
            if data is not None:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read(), response.headers.get("Content-Type", "")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError("unreachable")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_directory(year: int, department_id: int | None = None):
    rows, pages = [], []
    for page_no in range(1, MAX_PAGES + 1):
        args = {"skipAuth": "1", "YEARS": str(year), "queryPage__": f"{page_no},{PAGE_SIZE}"}
        if department_id is not None:
            args["DEPART_IDS"] = str(department_id)
        url = BASE + "/page-center/major-program-search-view/search?" + urllib.parse.urlencode(args)
        body, ctype = request(url)
        payload = json.loads(body.decode("utf-8-sig"))
        part = payload.get("data")
        if not isinstance(part, list):
            raise ValueError(f"directory response has no data list: {url}")
        meta = payload.get("_page_", {})
        if meta.get("currentPage") not in (None, page_no):
            raise ValueError(f"unexpected directory page number: {url} {meta}")
        if int(meta.get("rowsInPage", len(part))) != len(part):
            raise ValueError(f"rowsInPage mismatch: {url}")
        path = f"raw/directory-{('all' if department_id is None else 'department-' + str(department_id))}-page-{page_no}.json"
        # Preserve the exact public response bytes rather than reserializing JSON.
        target = current_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        page_record = {
            "path": path,
            "url": url,
            "content_type": ctype,
            "bytes": len(body),
            "sha256": sha256(body),
            "current_page": meta.get("currentPage", page_no),
            "rows_in_page": len(part),
            "total_rows": meta.get("totalRows"),
            "total_pages": meta.get("totalPages"),
        }
        pages.append(page_record)
        rows.extend(part)
        total = meta.get("totalRows")
        total_pages = meta.get("totalPages")
        if total_pages is not None:
            if page_no >= int(total_pages):
                if total is not None and len(rows) != int(total):
                    raise ValueError(f"directory totalRows mismatch: got {len(rows)}, expected {total}")
                break
        elif len(part) < PAGE_SIZE:
            if total is not None and len(rows) != int(total):
                raise ValueError(f"directory totalRows mismatch: got {len(rows)}, expected {total}")
            break
    else:
        raise ValueError(f"directory exceeded {MAX_PAGES} pages for {year}")
    ids = [str(r.get("ID")) for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate IDs in directory for {year} department={department_id}")
    return rows, pages


def relevant_cross_department_candidates(rows: list[dict]) -> list[dict]:
    candidates = []
    for row in rows:
        title = str(row.get("NAME_ZH", ""))
        major = str(row.get("MAJOR_NAME", ""))
        combined = title + " " + major
        if row.get("DEPART_IDS") == DEPARTMENT_ID or row.get("DEPART_NAME") == DEPARTMENT_NAME:
            continue
        if any(token in combined for token in GENERIC_TERMS):
            continue
        terms = [term for term in RELATED_MAJOR_TERMS if term in major]
        if terms:
            candidates.append({
                "plan_id": str(row.get("ID")),
                "title": title,
                "department": row.get("DEPART_NAME"),
                "department_id": row.get("DEPART_IDS"),
                "major_name": major,
                "matched_major_terms": terms,
                "directory_row": row,
                "status": "not_downloaded_cross_department_candidate",
                "reason": "目录归属不为新闻学院；仅保留有明确新闻学院专业名称的候选记录以供人工审阅。",
            })
    return candidates


def extract_docx(year: int, pid: str, word_bytes: bytes, root: Path):
    word_path = root / "word-originals" / f"plan-{pid}.docx"
    word_path.parent.mkdir(parents=True, exist_ok=True)
    word_path.write_bytes(word_bytes)
    images = []
    with zipfile.ZipFile(word_path) as docx:
        bad = docx.testzip()
        if bad:
            raise ValueError(f"corrupt Word archive {pid}: {bad}")
        names = set(docx.namelist())
        document = ET.fromstring(docx.read("word/document.xml"))
        ns = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
            "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        paragraphs = document.findall(".//w:p", ns)
        text = "\n".join("".join((node.text or "") for node in para.findall(".//w:t", ns)) for para in paragraphs)
        text_path = root / "word-text" / f"plan-{pid}.txt"
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding="utf-8")

        rels_name = "word/_rels/document.xml.rels"
        relationships = {}
        if rels_name in names:
            rels = ET.fromstring(docx.read(rels_name))
            relationships = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
        fig_dir = root / "source-figures"
        for paragraph_index, para in enumerate(paragraphs):
            for blip in para.findall(".//a:blip", ns):
                rid = blip.attrib.get("{" + ns["r"] + "}embed")
                target = relationships.get(rid)
                if not target:
                    continue
                member = posixpath.normpath(posixpath.join("word", target.replace("\\", "/")))
                if member not in names:
                    raise ValueError(f"image relationship target missing in {pid}: {member}")
                image = docx.read(member)
                original_name = Path(member).name
                out_name = f"plan-{pid}-p{paragraph_index:03d}-{len(images)+1:02d}-{original_name}"
                image_path = fig_dir / out_name
                fig_dir.mkdir(parents=True, exist_ok=True)
                image_path.write_bytes(image)
                images.append({
                    "path": f"source-figures/{out_name}",
                    "member": member,
                    "relationship_id": rid,
                    "paragraph_index": paragraph_index,
                    "sha256": sha256(image),
                    "bytes": len(image),
                })
    return word_path, text_path, text, images


def collect_plan(year: int, row: dict, root: Path):
    pid = str(row["ID"])
    detail_url = BASE + "/major-program-search/info/" + urllib.parse.quote(pid) + "?skipAuth=1"
    raw_path = root / "raw" / f"plan-{pid}.json"
    if raw_path.is_file():
        body = raw_path.read_bytes()
        ctype = "application/json; reused from prior run"
    else:
        body, ctype = request(detail_url)
    payload = json.loads(body.decode("utf-8-sig"))
    model = payload.get("model", {})
    if str(model.get("id")) != pid or str(model.get("grade")) != str(year):
        raise ValueError(f"plan identity/year mismatch for {pid}: {model.get('id')} {model.get('grade')}")
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(body)

    export_url = BASE + "/major-program-search/export-word"
    prior_word = root / "word-originals" / f"plan-{pid}.docx"
    if prior_word.is_file() and prior_word.read_bytes()[:2] == b"PK":
        word_bytes = prior_word.read_bytes()
        word_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document; reused from prior run"
    else:
        export_body = urllib.parse.urlencode({"ids": pid}).encode("ascii")
        word_bytes, word_type = request(export_url, export_body)
    if not word_bytes[:2] == b"PK":
        raise ValueError(f"Word export did not return a DOCX archive for {pid}: {word_type}")
    word_path, text_path, word_text, images = extract_docx(year, pid, word_bytes, root)

    title = str(row.get("NAME_ZH", ""))
    if DEPARTMENT_ID != row.get("DEPART_IDS") or row.get("DEPART_NAME") != DEPARTMENT_NAME:
        raise ValueError(f"selected plan does not belong to {DEPARTMENT_NAME}: {pid}")
    scope_tags = []
    if "留学生" in title:
        scope_tags.append("international_student")
    if any(term in title for term in ("港澳台", "港澳台侨")):
        scope_tags.append("hong_kong_macao_taiwan_overseas_chinese")
    if "双学士" in title or "双学位" in title or "双学士" in str(row.get("MAJOR_NAME", "")):
        scope_tags.append("double_degree")
    if "本硕" in title or "本硕" in str(row.get("MAJOR_NAME", "")):
        scope_tags.append("bachelor_master_integrated")
    meta = {
        "plan_id": pid,
        "cohort": year,
        "title": title,
        "department": row.get("DEPART_NAME"),
        "department_id": row.get("DEPART_IDS"),
        "major_name": row.get("MAJOR_NAME"),
        "scope": "department",
        "scope_tags": scope_tags,
        "directory_row": row,
        "detail_url": detail_url,
        "export_url": export_url,
        "export_method": "POST ids=" + pid,
        "raw_path": raw_path.relative_to(root).as_posix(),
        "raw_bytes": len(body),
        "raw_sha256": sha256(body),
        "detail_content_type": ctype,
        "word_path": word_path.relative_to(root).as_posix(),
        "word_text_path": text_path.relative_to(root).as_posix(),
        "word_bytes": len(word_bytes),
        "word_sha256": sha256(word_bytes),
        "cohort_year_present_in_word_text": str(year) in word_text,
        "word_content_type": word_type,
        "images": images,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "api_model_scope_fields": {key: model.get(key) for key in ("id", "nameZh", "grade", "stdType", "cultivateType", "major", "department", "depart", "years", "auditState", "bizType") if key in model},
    }
    write_json(root / "metadata" / f"plan-{pid}.json", meta)
    return meta


def collect_year(year: int):
    global current_root
    root = OUT / str(year) / "official"
    root.mkdir(parents=True, exist_ok=True)
    current_root = root
    all_rows, all_pages = get_directory(year)
    dept_rows, dept_pages = get_directory(year, DEPARTMENT_ID)
    # Department ID query must agree exactly with the unfiltered public listing.
    expected = [row for row in all_rows if row.get("DEPART_IDS") == DEPARTMENT_ID and row.get("DEPART_NAME") == DEPARTMENT_NAME]
    if {str(r["ID"]) for r in dept_rows} != {str(r["ID"]) for r in expected}:
        raise ValueError(f"department-filter and all-directory rows differ for {year}")
    if len(dept_rows) != len(expected):
        raise ValueError(f"department-filter duplicates/missing rows for {year}")

    related = relevant_cross_department_candidates(all_rows)
    # Record the exact filtered rows in readable indices in addition to original pages.
    write_json(root / "raw" / "department-rows.json", dept_rows)
    write_json(root / "raw" / "cross-department-relevant-candidates.json", related)

    plans = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(collect_plan, year, row, root) for row in dept_rows]
        for future in concurrent.futures.as_completed(futures):
            plans.append(future.result())
    plans.sort(key=lambda item: (item["title"], item["plan_id"]))
    write_json(root / "programmes.json", plans)
    downloaded_ids = {p["plan_id"] for p in plans}
    if downloaded_ids != {str(r["ID"]) for r in dept_rows}:
        raise ValueError(f"downloaded plan set differs from department listing for {year}")

    audit = {
        "cohort": year,
        "department_id": DEPARTMENT_ID,
        "department_name": DEPARTMENT_NAME,
        "api_directory_url": BASE + "/page-center/major-program-search-view/search",
        "api_detail_template": BASE + "/major-program-search/info/{ID}?skipAuth=1",
        "api_word_export": BASE + "/major-program-search/export-word",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "pagination": {"page_size": PAGE_SIZE, "all_pages": all_pages, "department_pages": dept_pages},
        "all_directory_rows": len(all_rows),
        "department_directory_rows": len(dept_rows),
        "selected_department_plans": len(plans),
        "downloaded_original_json": len(plans),
        "downloaded_original_word": sum(1 for p in plans if (root / p["word_path"]).is_file()),
        "embedded_images": sum(len(p["images"]) for p in plans),
        "cross_department_candidates_listed_not_downloaded": len(related),
        "cross_department_candidate_path": "raw/cross-department-relevant-candidates.json",
        "not_downloaded_reason": "跨院候选仅作人工审阅记录；本批下载范围限定为官方目录中院系字段准确匹配新闻学院的培养方案。通识、公共及含新闻字样的泛方案不作为相关专业方案。",
        "plans": [{"id": p["plan_id"], "title": p["title"], "major_name": p["major_name"], "scope_tags": p["scope_tags"], "word_path": p["word_path"]} for p in plans],
    }
    write_json(root / "coverage.json", audit)
    print(json.dumps({"cohort": year, "directory_total": len(all_rows), "department_plans": len(dept_rows), "downloaded": len(plans), "related_cross_department_candidates": len(related), "images": audit["embedded_images"]}, ensure_ascii=True), flush=True)
    return audit


if __name__ == "__main__":
    summaries = []
    for cohort_year in YEARS:
        summaries.append(collect_year(cohort_year))
    write_json(OUT / "source-index.json", {
        "source": "Fudan undergraduate curriculum public management API",
        "department_id": DEPARTMENT_ID,
        "department_name": DEPARTMENT_NAME,
        "years": YEARS,
        "cohorts": [{"cohort": x["cohort"], "path": f"{x['cohort']}/official/coverage.json", "directory_total": x["all_directory_rows"], "department_plans": x["selected_department_plans"], "related_cross_department_candidates": x["cross_department_candidates_listed_not_downloaded"]} for x in summaries],
    })
