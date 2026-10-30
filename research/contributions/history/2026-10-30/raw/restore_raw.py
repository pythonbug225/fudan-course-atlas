"""Verify raw snapshots; optionally restore their published JSON without network access."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def check(data, size, digest, name):
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Integrity check failed: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New directory for restored publication data")
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    manifest = json.loads((base / "manifest.json").read_text("utf-8"))
    if args.output and args.output.exists():
        raise ValueError("Choose a new output directory to avoid overwriting existing files")
    if args.output:
        args.output.mkdir(parents=True)
    for entry in manifest["files"]:
        packed = (base / entry["stored_path"]).read_bytes()
        check(packed, entry["stored_bytes"], entry["stored_sha256"], entry["stored_path"])
        data = gzip.decompress(packed)
        check(data, entry["restored_bytes"], entry["restored_sha256"], entry["restored_path"])
        json.loads(data)
        if args.output:
            destination = args.output / entry["restored_path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    for entry in manifest["word_originals"]:
        data = (base / entry["path"]).read_bytes()
        check(data, entry["bytes"], entry["sha256"], entry["path"])
        if args.output:
            destination = args.output / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    print(json.dumps({"verification": "passed", "json_files": len(manifest["files"]),
                      "word_originals": len(manifest["word_originals"]), "restored": bool(args.output)}))


if __name__ == "__main__":
    main()
