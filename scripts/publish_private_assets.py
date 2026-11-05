"""Publish immutable private packs; read secrets from stdin and never persist them."""
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

cfg = json.loads(sys.stdin.readline())
base = cfg['base'].rstrip('/')
assert urllib.parse.urlsplit(base).scheme == 'https'
assert len(cfg['key']) >= 64
root = Path(cfg['directory'])
raw = (root / 'manifest.json').read_bytes()
manifest = json.loads(raw)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

opener = urllib.request.build_opener(NoRedirect)

def request(route, body=None):
    req = urllib.request.Request(base + route, data=body, headers={
        'User-Agent': 'FudanCourseAtlasAssetPublisher/2.0',
        'Origin': base,
        'X-Asset-Publish-Key': cfg['key'],
        'Content-Type': 'application/octet-stream',
    })
    for attempt in range(4):
        try:
            with opener.open(req, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
        time.sleep(2 * (attempt + 1))

request('/api/private-assets/import?name=manifest.json', raw)
print('Manifest staged; existing published files remain active.', flush=True)
missing = set(request('/api/private-assets/status')['missing'])
for index, pack in enumerate(manifest['packs']):
    assert re.fullmatch(r'pack-\d{3}\.bin', pack['name'])
    if pack['name'] not in missing:
        print(f"Already verified {index+1}/{len(manifest['packs'])}: {pack['name']}", flush=True)
        continue
    body = (root / pack['name']).read_bytes()
    assert len(body) == pack['size']
    assert hashlib.sha256(body).hexdigest() == pack['sha256']
    request('/api/private-assets/import?name=' + pack['name'], body)
    print(f"Validated and uploaded {index+1}/{len(manifest['packs'])}: {pack['name']}", flush=True)
status = request('/api/private-assets/status')
assert status['ready'] and not status['missing']
assert status['files'] == len(manifest['files'])
result = request('/api/private-assets/finalize', b'{}')
assert result['published'] and result['publisherRevoked']
try:
    request('/api/private-assets/status')
    raise AssertionError('Retired publication key still accepted')
except urllib.error.HTTPError as error:
    assert error.code == 401, error.code
result.update(keyRevoked=True, totalBytes=sum(p['size'] for p in manifest['packs']))
print(json.dumps(result), flush=True)
