"""Create a small offline reference archive with a verifiable file manifest."""
import hashlib
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
OUT = Path('D:/danxi/outputs/大数据学院_20261029')
OUT.mkdir(parents=True, exist_ok=True)
excluded = {'files_manifest.json', 'publication-receipt.json'}
files = sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded and p.suffix not in ('.zip', '.pyc'))
for p in files:
    if p.suffix in ('.json','.html','.md','.csv','.py','.cjs') or p.name in ('.gitignore','.gitattributes'):
        text=p.read_bytes().decode('utf8').replace('\r\n','\n').replace('\r','\n')
        if p.suffix=='.html': text='\n'.join(line.rstrip() for line in text.splitlines())+'\n'
        p.write_bytes(text.encode('utf8'))
manifest = [{'path':p.relative_to(HERE).as_posix(), 'bytes':p.stat().st_size, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
manifest_path = HERE / 'files_manifest.json'
manifest_path.write_text(json.dumps({'files':manifest, 'file_count':len(manifest), 'uncompressed_bytes':sum(x['bytes'] for x in manifest)}, ensure_ascii=False, indent=2), encoding='utf8')
archive = OUT / 'fudan-bigdata-20261029.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for p in files + [manifest_path]: z.write(p, p.relative_to(HERE).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for item in manifest:
        assert hashlib.sha256(z.read(item['path'])).hexdigest() == item['sha256']
receipt = {'archive':archive.name, 'bytes':archive.stat().st_size, 'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(), 'file_count':len(files)+1, 'zip_integrity_verified':True, 'manifest_hashes_verified':True}
(OUT / 'release-manifest.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(receipt, ensure_ascii=False))
