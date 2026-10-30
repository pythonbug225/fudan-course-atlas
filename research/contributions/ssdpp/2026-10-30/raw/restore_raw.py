"""Verify or restore the published, redacted acquisition JSON files offline."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

R=Path(__file__).resolve().parent
def verify(output=None):
    manifest=json.loads((R/'manifest.json').read_text('utf-8'))
    for row in manifest['files']:
        path=(R/row['stored_path']).resolve()
        assert path.is_relative_to(R.resolve())
        packed=path.read_bytes()
        assert len(packed)==row['stored_bytes'] and hashlib.sha256(packed).hexdigest()==row['stored_sha256']
        data=gzip.decompress(packed)
        assert len(data)==row['restored_bytes'] and hashlib.sha256(data).hexdigest()==row['restored_sha256']
        json.loads(data)
        if output:
            dest=(output/row['restored_path']).resolve()
            assert dest.is_relative_to(output.resolve())
            if dest.exists() and dest.read_bytes()!=data:raise RuntimeError('Refusing to overwrite different file: '+str(dest))
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    print(json.dumps({'raw_files_verified':len(manifest['files']),'counts':manifest['counts'],'output':str(output) if output else None}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    verify(parser.parse_args().output)
