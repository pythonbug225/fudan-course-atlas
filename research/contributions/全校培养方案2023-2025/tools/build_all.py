"""Build complete programme groups as their verified download manifests arrive."""
import argparse
import collections
import concurrent.futures
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
from build import build_year, write

ROOT = Path(__file__).resolve().parent
def run_one(path):
    root = Path(path)
    stats = build_year(root)
    graph = json.loads((root / "graph.json").read_bytes())
    courses = json.loads(gzip.decompress((root / "courses.json.gz").read_bytes()))
    manifest = json.loads((root / "programmes.json").read_bytes())
    metas = {str(p["id"]): p for p in manifest}
    checks = collections.Counter()
    indexed = collections.defaultdict(list)
    for r in courses["rows"]:
        indexed[r["plan"]].append(r)
    for p in graph["plans"]:
        pid = p["id"]
        assert p["word_sha256"] == metas[pid]["word_sha256"] and p["plan_json_sha256"] == metas[pid]["raw_archive_sha256"]
        src = json.loads(gzip.decompress((root / "raw" / f"plan-{pid}.json.gz").read_bytes()))["courseModules"]
        assert len(indexed[pid]) == sum(len(m.get("planCourses") or []) for m in src) == p["rows"]
        assert all(r["code"] == str((src[r["module"]]["planCourses"][r["row"]].get("course") or {}).get("code") or "").strip() for r in indexed[pid])
        ids = {r["id"] for r in indexed[pid]}
        for e in p["edges"]:
            assert e["from"] in ids and e["to"] in ids
            for target, locator in zip([e["from"], e["to"]], e["rows"]):
                _, _, mi, _, ci = locator.split("/")
                code = str((src[int(mi)]["planCourses"][int(ci)].get("course") or {}).get("code") or "").strip()
                assert (code or f"ROW:{pid}:{mi}:{ci}") == target
        if not p["edges"]:
            checks["plans_without_course_pairs"] += 1
        if p["unresolved"]:
            checks["plans_with_text_for_review"] += 1
        checks["verified_files"] += 2
    return stats | {"school": root.parent.name, "year": int(root.name), **dict(checks)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    counts = json.loads((ROOT / "directories/programme-ids.json").read_text("utf-8"))
    expected = {(school, year) for school, ys in counts.items() for year in ys}
    status_file = ROOT / "build-status.json"
    results = {}
    version = hashlib.sha256((ROOT/"build.py").read_bytes()+(ROOT/"build_all.py").read_bytes()+(ROOT/"extra-rules.json").read_bytes() if (ROOT/"extra-rules.json").exists() else (ROOT/"build.py").read_bytes()+(ROOT/"build_all.py").read_bytes()).hexdigest()
    if status_file.exists():
        old = json.loads(status_file.read_bytes())
        if old["version"] == version:
            results = {k:v for k,v in old["results"].items() if (ROOT / "data" / k / "graph.json").exists()}
    failed = {}
    with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
        while True:
            groups = sorted((ROOT / "data").glob("*/*/programmes.json"))
            pending = {p.parent.relative_to(ROOT / "data").as_posix():p.parent for p in groups if p.parent.relative_to(ROOT / "data").as_posix() not in results}
            jobs = {pool.submit(run_one,str(path)): key for key,path in pending.items()}
            for f in concurrent.futures.as_completed(jobs):
                key = jobs[f]
                try:
                    results[key] = f.result()
                    print("BUILT", key, results[key]["plans"], flush=True)
                    failed.pop(key,None)
                except Exception as e:
                    failed[key] = repr(e)
                    print("FAILED", key, str(e), flush=True)
                write(status_file,json.dumps({"version":version,"results":results,"failures":failed,"total":len(expected)},ensure_ascii=False,indent=2)+"\n")
            if len(results)==len(expected) or not args.watch:
                break
            if failed:
                raise RuntimeError(str(failed))
            time.sleep(4)
    print("COMPLETE",len(results),"/",len(expected),"failures",failed,flush=True)
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
