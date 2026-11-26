"""Verify the public curriculum archive against all three official directory responses."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def verify(root):
    directory = root / "directories"
    index = json.loads((directory / "coverage.json").read_bytes())
    expected = collections.defaultdict(dict)
    annual_totals = {}
    for call in index["calls"]:
        archive = (directory / call["file"]).read_bytes()
        assert digest(archive) == call["archive_sha256"], call["file"]
        response = gzip.decompress(archive)
        assert digest(response) == call["response_sha256"], call["file"]
        raw = json.loads(response)
        assert len(raw["data"]) == call["returned_rows"], call["file"]
        for row in raw["data"]:
            year = int(row["YEARS"])
            group = expected[(row["DEPART_NAME"],year)]
            assert row["ID"] not in group, row["ID"]
            group[row["ID"]] = row
            annual_totals[year] = int(raw["_page_"]["totalRows"])
    checked = {}
    totals = collections.Counter()
    for (dept, year), rows in sorted(expected.items()):
        group = root / "data" / dept / str(year)
        records = json.loads((group / "programmes.json").read_bytes())
        assert {p["id"] for p in records} == set(rows) and len(records) == len(rows), (dept,year)
        assert {p.name for p in (group / "raw").glob("plan-*.json.gz")} == {f"plan-{pid}.json.gz" for pid in rows}
        assert {p.name for p in (group / "originals").glob("plan-*.docx")} == {f"plan-{pid}.docx" for pid in rows}
        for record in records:
            pid = record["id"]
            row = rows[pid]
            assert year == record["year"] and row["NAME_ZH"] == record["title"] and row["DEPART_IDS"] == record["department_id"], pid
            source = (group / record["raw_file"]).read_bytes()
            word = (group / record["word_file"]).read_bytes()
            assert digest(source) == record["raw_archive_sha256"], pid
            assert digest(word) == record["word_sha256"] and len(word) == record["word_bytes"], pid
        checked.setdefault(dept,{})[year] = len(records)
        totals[year] += len(records)
    assert dict(totals) == annual_totals, (totals,annual_totals)
    return {
        "passed": True,
        "directory_retrieved": index["retrieved"],
        "cohorts": dict(sorted(totals.items())),
        "departments_or_teaching_units": len(checked),
        "year_department_groups": len(expected),
        "plans": sum(totals.values()),
        "word_originals_verified": sum(totals.values()),
        "raw_detail_archives_verified": sum(totals.values()),
        "scope": "Public directory check: all row IDs matched by year and department, and both files matched the SHA-256 recorded on acquisition. Previously archived non-directory sources are outside this check.",
        "per_department": checked,
    }


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root",nargs="?",type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=verify(args.root)
    if args.output:
        args.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode())
    print(f"{result['plans']} plans, {result['year_department_groups']} groups, {result['departments_or_teaching_units']} departments/units; all hashes matched.")
