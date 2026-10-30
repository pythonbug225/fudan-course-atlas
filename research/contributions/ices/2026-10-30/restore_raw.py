"""Restore and verify the public, redacted captured JSON files (offline)."""
import argparse,gzip,hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parent
def verify(output=None):
    manifest=json.loads((R/'raw/manifest.json').read_text('utf8'))
    for row in manifest['files']:
        packed=(R/'raw'/row['stored_path']).read_bytes()
        assert len(packed)==row['stored_bytes'] and hashlib.sha256(packed).hexdigest()==row['stored_sha256'],row['stored_path']
        data=gzip.decompress(packed)
        assert len(data)==row['restored_bytes'] and hashlib.sha256(data).hexdigest()==row['restored_sha256'],row['source_path']
        json.loads(data)
        if output:
            dest=output/row['source_path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    print(json.dumps({'raw_files_verified':len(manifest['files']),'counts':manifest['counts'],'output':str(output) if output else None},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path);verify(p.parse_args().output)
