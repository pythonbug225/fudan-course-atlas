"""Build the SIRPA contribution from locally collected sources; no network/login."""
import argparse, collections, hashlib, importlib.util, json, pathlib, re

ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('raw_export',pathlib.Path(__file__).with_name('build_raw_archive.py'))
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
LICENSE='https://danxi.fduhole.com/doc/community-user-agreement'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def write(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf-8')
def digest(x):return hashlib.sha256(x).hexdigest()

def build(workspace):
    w=workspace/'work/sirpa-research';o=workspace/'outputs/复旦国务学院2026培养方案与课程研究'
    dest=ROOT/'research/contributions/sirpa/2026-10-27';dest.mkdir(parents=True,exist_ok=True)
    changes=collections.Counter()
    def clean(x,category='research-ledgers'):
        x=export.sanitize(x,changes,category)
        if isinstance(x,str):
            return re.sub(r'(?i)(?:\+\s*v|加\s*v|wechat)\s*[,，:：=]?\s*[A-Za-z0-9_-]{5,}','[联系方式已脱敏]',x)
        if isinstance(x,list):return [clean(v,category) for v in x]
        if isinstance(x,dict):return {k:clean(v,category) for k,v in x.items()}
        return x
    summaries={
        'danke-summaries.json':'实时蛋壳评价核读摘要.json',
        'forum-summaries.json':'树洞讨论核读摘要.json',
        'target-term-comparisons.json':'目标学期课程比较总结.json',
        'public-comparisons.json':'公开课程比较总结.json',
        'public-sources.json':'公开平台已读证据.json',
        'browser-sources.json':'浏览器站内检索与已读证据.json',
        'coverage.json':'检索与阅读覆盖.json',
    }
    for name,src in summaries.items():write(dest/'summaries'/name,clean(read(o/src)))
    roster=read(w/'official/教学班清单_2025秋-2026春.json')
    write(dest/'official/sections.json',clean(roster))
    write(dest/'official/syllabi.json',clean(read(o/'官方培养方案/官方大纲结构化摘要.json')))
    write(dest/'official/programs.json',clean(read(o/'官方培养方案/培养方案下载清单.json')))
    ds=read(o/'实时蛋壳评价核读摘要.json')['sources'];fs=read(o/'树洞讨论核读摘要.json')['sources']
    dr=read(w/'live/danke_details_results.json');fr=read(w/'live/forum_context_results.json')
    raw_reviews=[]
    for s in ds:
        item=dr['reviews'][str(s['review_id'])]
        raw_reviews.append({'review_id':s['review_id'],'source_url':s['url'],'fetched_at':'2026-10-27','response':clean(item['data'],'danke'),'course_records':[clean(dr['courses'][str(c)]['data'],'danke') for c in item.get('course_ids',[])], 'public_author_label':None,'attribution_note':'原抓取未保留署名；作者署名未确认，不补造。原作者与原帖出处以source_url定位。','license':'CC BY 4.0 unless author states otherwise','license_basis_url':LICENSE,'changes':'删除身份/凭证字段、联系方式和签名链接；限制转载或已删除正文按公开导出规则隐藏。'})
    floor_refs=collections.defaultdict(list)
    for s in fs:
        for fid in s['floor_ids']:floor_refs[str(fid)].append(s['id'])
    raw_floors=[]
    for fid,refs in sorted(floor_refs.items(),key=lambda p:int(p[0])):
        data=fr['floors'][fid]['data']
        raw_floors.append({'floor_id':int(fid),'hole_id':data['hole_id'],'source_url':'https://forum.fduhole.com/api/floors/'+fid,'summary_source_ids':sorted(set(refs)),'fetched_at':'2026-10-27','response':clean(data,'treehole'),'public_author_label':None,'attribution_note':'匿名原帖；原抓取未保留作者署名，未补造。','license':'CC BY 4.0 unless author states otherwise','license_basis_url':LICENSE,'changes':'仅导出已采用/保留来源实际引用的楼层，不导出全量搜索命中。删除身份/凭证字段与联系方式，限制转载/删除正文隐藏。'})
    for name,records in [('danke-reviews.jsonl',raw_reviews),('treehole-cited-floors.jsonl',raw_floors)]:
        p=dest/'raw'/name;p.parent.mkdir(exist_ok=True)
        p.write_text(''.join(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n' for x in records),'utf-8')
    sources=ds+fs+read(o/'公开平台已读证据.json')['sources']+read(o/'浏览器站内检索与已读证据.json')['sources']
    profiles=read(o/'目标学期课程比较总结.json').get('courses',[])+read(o/'公开课程比较总结.json').get('courses',[])
    grouped=collections.defaultdict(list)
    for r in roster:grouped[r['course_code']].append(r)
    for code,sections in sorted(grouped.items()):
        chosen=[s for s in sources if code in s.get('course_codes',[])]
        record={'schema_version':1,'course':{'code':code,'name':sections[0]['course_name'],'department':'国际关系与公共事务学院','terms':sorted({s['term'] for s in sections}),'teachers':sorted({t.strip() for s in sections for t in s['teachers'].split('/') if t.strip()}),'sections':sections},'progress':{'status':'reviewed_batch_with_gaps','reading_date':'2026-10-27','no_student_reviews_found':False,'remaining_scope':['未穷尽所有平台及别名；无已读证据不等于无评价。']},'sources':chosen,'student_reviews_and_discussions':[s for s in chosen if s in ds or s in fs],'comparison_and_summary':[p for p in profiles if code in p.get('course_codes',[])],'official_syllabus_locator':'../official/syllabi.json','raw_evidence_locators':['../raw/danke-reviews.jsonl','../raw/treehole-cited-floors.jsonl'],'mapping_policy':'未知教师、期别冲突和多课号候选不解释为唯一目标班；发帖日期不推定修读学期。'}
        write(dest/'courses'/f'{code}.json',clean(record))
    # Logs contain executed query text and status, never response bodies or sessions.
    for category in ['danke','forum']:
        ledger=read(w/f'live/{category}_search_ledger.json')
        queries=[{k:v for k,v in q.items() if k in ['query_id','query','course_codes','status','pages_fetched','attempts','error']} for q in ledger['queries'].values()]
        write(dest/f'ledgers/{category}-queries.json',clean({'queries':queries,'note':'status=in_progress为中止时快照；不是已完成。计划数与实际执行数分别统计。'}))
    public_queries=[]
    for name in ['course_search_log.json','graduate_search_log.json']:
        for batch in read(w/'public'/name)['batches']:public_queries.extend(batch['queries'])
    write(dest/'ledgers/public-web-queries.json',clean(public_queries))
    files=[]
    for p in sorted(dest.rglob('*')):
        if p.is_file() and p.name!='manifest.json':files.append({'path':p.relative_to(dest).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())})
    manifest={'schema_version':1,'batch':'sirpa-2026-10-27','course_codes':len(grouped),'sections':len(roster),'danke_raw_reviews':len(raw_reviews),'treehole_cited_raw_floors':len(raw_floors),'treehole_fully_read_holes':309,'treehole_fully_read_floors':3280,'raw_export_scope':'原始响应字段经明确脱敏，不是摘要重写；搜索命中、未采用上下文及外部平台全文不发布。','raw_attribution_limit':'旧抓取未保留作者字段，不补造署名；公开原帖URL和来源ID保留。','redactions':dict(changes),'files':files}
    write(dest/'manifest.json',manifest)
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--workspace',type=pathlib.Path,required=True)
    m=build(p.parse_args().workspace.resolve());print(json.dumps({k:m[k] for k in ['course_codes','sections','danke_raw_reviews','treehole_cited_raw_floors']},ensure_ascii=False))
