"""Export the existing acquisition cache offline, preserving IDs and query associations."""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode=True
R=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('archive',R.parents[4]/'scripts/research/build_raw_archive.py')
archive=importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
archive.SECRET_KEYS.update({'mention','authorid','uid','liked','disliked','favorited','subscribed'})
archive.BODY_FIELDS.add('highlighted_content')
archive.NO_REPRINT=re.compile(archive.NO_REPRINT.pattern+r'|禁止搬运|请勿搬运|未经.{0,12}(?:许可|允许|同意).{0,8}(?:转发|搬运)')
original_public_url=archive.public_url

def public_url(value,changes):
    # Sogou/WeChat article signatures identify the article, not a logged-in session.
    if urlsplit(value).hostname=='mp.weixin.qq.com':
        archive.SIGNED_PARAMS.discard('signature')
        try:return original_public_url(value,changes)
        finally:archive.SIGNED_PARAMS.add('signature')
    return original_public_url(value,changes)

def clean_text(value,changes):
    # Do not confuse public article IDs in URLs with student numbers or phone numbers.
    urls=[]
    def hold(match):
        urls.append(public_url(match.group(),changes))
        return '[PUBLIC_URL_'+str(len(urls)-1)+']'
    value=archive.URL_RE.sub(hold,value)
    for name,pattern in archive.CONTACT_PATTERNS:
        value,count=pattern.subn('[已脱敏]',value)
        changes[name]+=count
    for i,url in enumerate(urls):value=value.replace('[PUBLIC_URL_'+str(i)+']',url)
    return value

archive.clean_text=clean_text
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(v):return (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode('utf-8')
def write_json(p,v):p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def true(v):return v in (True,1,'true')

def run(source):
    evidence=read(R.parent/'summaries/evidence.json')
    approved_holes={int(e['hole_id']) for e in evidence if e.get('hole_id')}
    context=read(source/'live/forum_context_results.json')
    hidden_holes={int(k) for k,v in context['holes'].items() if any(true(v['data'].get(f)) for f in ('hidden','deleted','frozen')) or v['data'].get('time_deleted')}
    counts=collections.Counter();changes_total=collections.Counter();index=[]
    files=[]
    for p in sorted((source/'official-scope').glob('*-raw.json')):
        files.append((p,'official/'+p.name,'official-response'))
    for p in sorted((source/'official-scope/plans').glob('*-detail.json')):
        files.append((p,'official/plans/'+p.name,'official-response'))
    for p in sorted((source/'live').glob('*.json')):
        files.append((p,'live/'+p.name,'research-ledgers' if 'ledger' in p.name else 'treehole' if p.name.startswith('forum') else 'danke'))
    for p in sorted((source/'live-jobs').glob('*.json')):
        files.append((p,'query-plans/'+p.name,'research-ledgers'))
    for p in sorted((source/'public').glob('*.json')):
        files.append((p,'public-search-observations/'+p.name,'external-web'))
    for p in sorted((source/'browser-recovery').glob('*/*.json')):
        files.append((p,'browser-observations/'+p.parent.name+'/'+p.name,'external-web'))
    for p in sorted((source/'readers').glob('reviewed_*.json')):
        files.append((p,'reading-ledgers/'+p.name,'research-ledgers'))
    for p,logical,category in files:
        original=p.read_bytes();value=json.loads(original.decode('utf-8-sig'));changes=collections.Counter()
        if p.name in {'forum_search_results.json','forum_context_results.json'}:
            items=value['items'] if 'items' in value else value['floors'].values()
            for item in items:
                data=item['data'];fid=data.get('id',item['id']);hid=data.get('hole_id')
                item['source_urls']=list(dict.fromkeys(item.get('source_urls',[])+['https://forum.fduhole.com/api/floors/'+str(fid)]))
                restricted=hid in hidden_holes or any(true(data.get(k)) for k in ('deleted','fold','is_sensitive','is_actual_sensitive'))
                no_reprint=archive.NO_REPRINT.search('\n'.join(str(data.get(k,'')) for k in archive.BODY_FIELDS))
                reason='restricted_or_deleted' if restricted else 'author_restricts_republication' if no_reprint else 'course_context_not_verified' if hid not in approved_holes else None
                if reason:
                    for key in archive.BODY_FIELDS:
                        if key in data:data[key]='[正文未公开：'+reason+']'
                    item['public_body_status']=reason
                    counts['forum_bodies_withheld_'+reason]+=1
                else:
                    item['public_body_status']='course_related_body_retained_with_redactions'
                    counts['forum_body_instances_retained']+=1
        elif p.name=='danke_details_results.json':
            for rid,item in value['reviews'].items():
                item['source_urls']=list(dict.fromkeys(item.get('source_urls',[])+['https://danke.fduhole.com/api/reviews/'+rid]))
                item['public_body_status']='captured_review_not_necessarily_human_read'
        value=archive.sanitize(value,changes,category)
        # Keep original JSON bytes when no publication transformation was necessary.
        data=original if category=='official-response' and not +changes else encode(value)
        packed=gzip.compress(data,compresslevel=9,mtime=0)
        dest=R/(logical+'.gz');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(packed)
        index.append({'source_path':p.relative_to(source).as_posix(),'category':category,
                      'stored_path':logical+'.gz','restored_path':logical,
                      'captured_bytes':len(original),'captured_sha256':sha(original),
                      'stored_bytes':len(packed),'stored_sha256':sha(packed),
                      'restored_bytes':len(data),'restored_sha256':sha(data),
                      'byte_identical_to_capture':data==original,'redactions':dict(+changes)})
        changes_total.update(changes)
    forum=read(source/'live/forum_search_results.json')
    danke=read(source/'live/danke_details_results.json')
    manifest={'schema':'ssdpp-source-responses/1','capture_date':'2026-10-30','files':index,
        'file_count':len(index),'redactions':dict(+changes_total),'forum_body_counts':dict(counts),
        'counts':{'official_responses':18,'official_word_originals':15,'official_sections':391,
                  'forum_search_candidates':len(forum['items']),'forum_context_holes':len(context['holes']),
                  'forum_context_floors':len(context['floors']),
                  'danke_search_groups':len(read(source/'live/danke_search_results.json')['items']),
                  'danke_detail_groups':len(danke['groups']),'danke_courses':len(danke['courses']),
                  'danke_reviews':len(danke['reviews']),'queries_per_service':2029,
                  'course_context_approved_holes':len(approved_holes)},
        'license_source':archive.LICENSE_URL,'license_checked_date':'2026-10-30',
        'license_note':'Community original text defaults to CC BY 4.0 unless the author says otherwise. Source links and captured anonymous labels are retained. Third-party quotations, official documents and external websites retain their own rights.',
        'transformations':['Captured result structure, IDs, query associations and timestamps are retained; this is an export of saved acquisition caches, not reconstructed HTTP traffic.',
            'Credentials, account/profile/contact fields and personal contact text are removed. Public article IDs in URLs are preserved.',
            'Forum bodies are published only within already verified course-related threads. Other hits keep metadata and query association with explicit public_body_status. Restricted, deleted and no-reprint bodies are withheld.',
            'External-platform records are actual search/reading observations and source links; they are not original HTML, screenshots or article full text.',
            'Captured and restored hashes differ when a file was sanitized, canonicalized or annotated. gzip is lossless for the published restored JSON.']}
    write_json(R/'manifest.json',manifest)
    words=[]
    for p in sorted((source/'official-scope/plans').glob('*.docx')):
        words.append({'path':'official/word-originals/'+p.name,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes()),
                      'source_url':next(x['导出接口'] for x in read(source/'official-scope/培养方案下载清单.json') if str(x['方案编号']) in p.stem)})
    write_json(R/'word-originals.json',words)
    print(json.dumps({'files':len(index),'compressed_bytes':sum(x['stored_bytes'] for x in index),'counts':manifest['counts'],'body_counts':dict(counts),'redactions':dict(+changes_total)},ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--source-dir',type=Path,required=True)
    run(parser.parse_args().source_dir)
