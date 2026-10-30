"""Verify or restore the published redacted source responses, offline (stdlib only)."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath

BATCH = Path(__file__).resolve().parent


def safe_path(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative or ":" in relative:
        raise ValueError("Unsafe manifest path")
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Manifest path escapes destination")
    return result


def verify(output=None):
    root = BATCH / "raw"
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    restored_files = []
    for row in manifest["files"]:
        packed = safe_path(root, row["stored_path"]).read_bytes()
        assert len(packed) == row["stored_bytes"] and hashlib.sha256(packed).hexdigest() == row["stored_sha256"], row["stored_path"]
        raw = gzip.decompress(packed)
        assert len(raw) == row["restored_bytes"] and hashlib.sha256(raw).hexdigest() == row["restored_sha256"], row["source_path"]
        json.loads(raw)
        restored_files.append((row, raw))
    assert len(restored_files) == manifest["file_count"]
    # Verify all inputs first; existing files must match, never overwrite researcher data.
    if output:
        for row, raw in restored_files:
            dest = safe_path(output, row["source_path"])
            if dest.exists() and dest.read_bytes() != raw:
                raise FileExistsError("Restore would overwrite a different file: " + str(dest))
        for row, raw in restored_files:
            dest = safe_path(output, row["source_path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
    print(json.dumps({"status": "passed", "source_files": len(restored_files), "unique_post_counts": manifest["unique_post_counts"], "output": str(output) if output else None}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional destination for decompressed JSON files")
    verify(parser.parse_args().output)
