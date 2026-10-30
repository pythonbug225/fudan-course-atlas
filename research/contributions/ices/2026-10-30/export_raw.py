"""Offline export of this batch's captured source responses; no network access."""
import argparse,collections,gzip,hashlib,importlib.util,json,pathlib,copy
R=pathlib.Path(__file__).resolve().parent
repo=R.parents[3]
spec=importlib.util.spec_from_file_location('archive',repo/'scripts/research/build_raw_archive.py')
archive=importlib.util.module_from_spec(spec);spec.loader.exec_module(archive)
def encode(x):return (json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf8')
def sha(x):return hashlib.sha256(x).hexdigest()
def run(source):
    target=R/'raw';target.mkdir(exist_ok=True)
    # Publish full forum bodies only for course-related threads already read.
    adopted=json.loads((R/'已核读课评摘要.json').read_text('utf8'))
    questions=json.loads((R/'课程咨询索引.json').read_text('utf8'))
    approved_holes={e['hole_id'] for e in adopted if e.get('hole_id')}|{q['hole_id'] for q in questions}|{351293}
    index=[];total=collections.Counter();body_counts=collections.Counter()
    files=[(p,'treehole' if p.name.startswith('forum') else 'danke','live/'+p.name) for p in sorted((source/'live').glob('*.json'))]
    files += [(p,'research-ledgers','query-plans/'+p.name) for p in sorted((source/'live-jobs').glob('*.json'))]
    files += [(p,'official-programs-and-outlines','official/'+p.name) for p in sorted((source/'official/原始接口').glob('*.json'))]
    for p,category,logical in files:
        original=p.read_bytes();value=json.loads(original.decode('utf-8-sig'));changes=collections.Counter()
        if p.name=='forum_search_results.json':
            for item in value['items']:
                data=item['data'];fid=data.get('id',item['id']);hid=data.get('hole_id')
                item['source_url']='https://forum.fduhole.com/api/floors/'+str(fid)
                if hid not in approved_holes or data.get('is_sensitive') or data.get('is_actual_sensitive') or data.get('deleted') or data.get('fold'):
                    for field in ['content','highlighted_content']:
                        if field in data:data[field]='[正文未公开：尚未完成课程相关性或隐私核对]'
                    item['public_body_status']='withheld_unreviewed_or_sensitive_candidate';body_counts['search_bodies_withheld']+=1
                else:item['public_body_status']='read_course_thread_body';body_counts['search_bodies_retained']+=1
        elif p.name=='forum_context_results.json':
            for fid,item in value['floors'].items():
                data=item['data'];hid=data.get('hole_id')
                item['source_urls']=list(dict.fromkeys(item.get('source_urls',[])+['https://forum.fduhole.com/api/floors/'+str(fid)]))
                if hid not in approved_holes or data.get('deleted') or data.get('fold'):
                    for field in ['content','highlighted_content']:
                        if field in data:data[field]='[正文未公开：尚未完成课程相关性或隐私核对]'
                    item['public_body_status']='withheld_unreviewed_or_sensitive_candidate';body_counts['context_bodies_withheld']+=1
                else:item['public_body_status']='read_course_thread_body';body_counts['context_bodies_retained']+=1
        value=archive.sanitize(value,changes,category)
        data=encode(value);packed=gzip.compress(data,compresslevel=9,mtime=0)
        rel=logical+'.gz';dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(packed)
        index.append({'source_path':logical,'category':category,'captured_bytes':len(original),'captured_sha256':sha(original),'stored_path':rel,'stored_bytes':len(packed),'stored_sha256':sha(packed),'restored_bytes':len(data),'restored_sha256':sha(data),'redactions':dict(+changes),'read_status':'captured does not mean read; see per-record public_body_status and reading ledgers'})
        total.update(changes)
    summary={'schema':'ices-source-responses/1','capture_date':'2026-10-30','files':index,'file_count':len(index),'redactions':dict(+total),'forum_body_counts':dict(body_counts),'counts':{'forum_search_candidates':19632,'forum_context_holes':63,'forum_context_floors':502,'danke_search_groups':616,'danke_detail_groups':369,'danke_courses':776,'danke_reviews':11,'current_queries_per_service':1361},'license_source':'https://danxi.fduhole.com/doc/community-user-agreement','license_note':'Community text default CC BY 4.0 unless authors state otherwise; source links and supplied anonymous labels retained. Deleted/restricted text withheld; identity/contact fields removed. Attribution absent from the captured cache is not invented. Official and external materials retain their own rights.','transformations':['Captured JSON structures and all result IDs/associations are retained; credential/identity/contact fields are removed.','Forum candidates not approved through course-thread reading retain metadata, query association and source URLs but omit body text.','Captured SHA-256 refers to the local acquisition file; restored SHA-256 refers to the public redacted canonical JSON, so these need not match.','No external-platform article full text or images were saved as a publishable raw capture; only real queries and reading logs are provided.']}
    (target/'manifest.json').write_bytes(json.dumps(summary,ensure_ascii=False,indent=2).encode('utf8')+b'\n')
    print(json.dumps({'raw_files':len(index),'compressed_bytes':sum(x['stored_bytes'] for x in index),'forum_body_counts':dict(body_counts),'redactions':dict(+total)},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-dir',required=True,type=pathlib.Path);run(p.parse_args().source_dir)
