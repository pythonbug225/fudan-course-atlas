"""Read/write the catalogue's lossless ordered source chunks for import tools."""
import json,re
from pathlib import Path

def read_catalog(file):
    file=Path(file)
    data=json.loads(file.read_text(encoding='utf-8-sig'))
    if 'catalog_parts' not in data:return data
    parts=data.pop('catalog_parts')
    if not parts or any(not re.fullmatch(r'catalog-scope-\d+\.json',p)for p in parts):
        raise ValueError('Invalid catalogue chunk index')
    data['scope']=[row for p in parts for row in json.loads((file.parent/p).read_text(encoding='utf8'))['scope']]
    if len(data['scope'])!=data['stats']['course_code_groups']:raise ValueError('Incomplete catalogue')
    return data

def write_catalog(file,data):
    file=Path(file)
    parts=[];chunk=[];size=12
    def flush():
        nonlocal chunk,size
        if not chunk:return
        name=f'catalog-scope-{len(parts)+1:03}.json'
        (file.parent/name).write_text(json.dumps({'scope':chunk},ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
        parts.append(name);chunk=[];size=12
    for row in data['scope']:
        n=len(json.dumps(row,ensure_ascii=False,separators=(',',':')).encode('utf8'))+1
        if size+n>4*1024*1024:flush()
        chunk.append(row);size+=n
    flush()
    manifest={k:v for k,v in data.items()if k!='scope'};manifest['catalog_parts']=parts
    file.write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
