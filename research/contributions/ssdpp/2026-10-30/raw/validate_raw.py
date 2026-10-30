"""Check restored hashes, acquisition counts and residual private fields; no network."""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zipfile

sys.dont_write_bytecode=True
import export_raw as ex
import restore_raw
R=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text('utf-8'))
def raw(name):return json.loads(gzip.decompress((R/name).read_bytes()))
def run(source=None,archive=None):
    restore_raw.verify()
    manifest=load(R/'manifest.json');issues=[];retained=set();files={}
    def walk(value,location):
        if isinstance(value,dict):
            for k,v in value.items():
                if ex.archive.keyform(k) in ex.archive.SECRET_KEYS:issues.append((location,k,'private_field'))
                walk(v,location+'/'+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,location+'/'+str(i))
        elif isinstance(value,str):
            change=collections.Counter()
            ex.clean_text(value,change)
            if +change:issues.append((location,dict(+change)))
    for entry in manifest['files']:
        value=raw(entry['stored_path']);files[entry['restored_path']]=value
        walk(value,entry['stored_path'])
        if source:
            original=(source/entry['source_path']).read_bytes()
            assert len(original)==entry['captured_bytes'] and ex.sha(original)==entry['captured_sha256']
    search=files['live/forum_search_results.json']['items']
    context=files['live/forum_context_results.json']
    reviews=files['live/danke_details_results.json']['reviews']
    assert len(search)==57587 and len(context['holes'])==106 and len(context['floors'])==1597
    assert len(reviews)==99
    assert len(files['live/danke_search_results.json']['items'])==1072
    assert len(files['live/danke_details_results.json']['groups'])==468
    assert len(files['live/danke_details_results.json']['courses'])==2016
    for service in ['forum','danke']:
        queries=files['live/'+service+'_search_ledger.json']['queries']
        assert len(queries)==2029 and all(q['status']=='completed' for q in queries.values())
    for item in list(search)+list(context['floors'].values()):
        if item['public_body_status']=='course_related_body_retained_with_redactions':
            assert item['data'].get('content') and not item['data'].get('deleted')
            retained.add(item['id'])
        else:
            assert item['data'].get('content','').startswith('[正文未公开：')
    if source:
        for name in ['forum_search_results.json','danke_search_results.json']:
            captured=load(source/'live'/name)['items'];published=files['live/'+name]['items']
            assert len(captured)==len(published)
            assert [(i['id'],i.get('query_ids'),i.get('course_codes')) for i in captured]==[(i['id'],i.get('query_ids'),i.get('course_codes')) for i in published]
        for name,keys in [('forum_context_results.json',['holes','floors']),('danke_details_results.json',['groups','courses','reviews'])]:
            captured=load(source/'live'/name);published=files['live/'+name]
            for key in keys:assert set(captured[key])==set(published[key])
    if archive:
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for entry in manifest['files']:
                data=z.read('ssdpp-raw-data-20261030/'+entry['restored_path'])
                assert ex.sha(data)==entry['restored_sha256']
            for entry in load(R/'word-originals.json'):
                data=z.read('ssdpp-raw-data-20261030/'+entry['path'])
                assert len(data)==entry['bytes'] and ex.sha(data)==entry['sha256']
    report={'passed':not issues,'files_verified':len(manifest['files']),
            'retained_unique_forum_floors':len(retained),'issues':issues,
            'source_hashes_and_result_ids_verified':source is not None,
            'archive_and_word_originals_verified':archive is not None}
    ex.write_json(R/'audit-report.json',report)
    print(json.dumps(report,ensure_ascii=False))
    if issues:raise SystemExit(1)
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path);p.add_argument('--archive',type=Path)
    args=p.parse_args();run(args.source_dir,args.archive)
