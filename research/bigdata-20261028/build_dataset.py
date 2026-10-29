"""Build an attributable department dataset from local reviewed source exports.

Run from any directory. Raw chat logs, credentials, and access tokens are never
included; the checked-in dataset contains only reviewed, de-identified records.
"""
from collections import defaultdict
from pathlib import Path
import json
import re
from html.parser import HTMLParser

HERE = Path(__file__).resolve().parent
PRIVATE = Path('D:/danxi/课程评价整理_20261023/补充核验')
ROOT = PRIVATE / '大数据学院_20261028'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf8'))

class Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
    def handle_data(self, value):
        self.parts.append(value)
    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'li', 'tr'):
            self.parts.append('\n')

def clean(s):
    parser = Text(); parser.feed(s or '')
    text = ''.join(parser.parts).strip()
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[联系方式已隐去]', text)
    text = re.sub(r'(?<!\d)1[3-9]\d{9}(?!\d)', '[联系方式已隐去]', text)
    return re.sub(r'\n{3,}', '\n\n', text)

scope = read(ROOT / 'chat_work/course_scope_snapshot_extract.json')
bycode = {r['course_code']: {'code': r['course_code'], 'name': r['course_name'], 'department': '大数据学院', 'terms': r['terms'], 'teachers': r['teachers'], 'search_aliases': [a['value'] for a in r.get('aliases', []) if a.get('kind') in ('course_full_pinyin', 'course_initials')], 'offerings': [], 'plan_refs': [], 'syllabi': [], 'materials': [], 'reviews': [], 'honor': r['course_code'].lower().endswith('h')} for r in scope['courses']}
official = {}
enrollment = {}
for termid in (504, 505):
    d = read(PRIVATE / f'化学系_20261027/official_index_{termid}.json')
    official.update({r['id']: r for r in d['rows'] if (r.get('department') or {}).get('nameZh') == '大数据学院'})
    ep = PRIVATE / f'深查与选课人数_20261025/enrollment_private/{termid}.json'
    if ep.exists():
        ed = read(ep)
        enrollment.update({(termid, r['id']):r | {'snapshot_at':ed.get('fetched_at')} for r in ed['rows']})
for o in scope['offerings']:
    raw = official[o['offering_id']]; course = bycode[o['course_code']]
    people = [t['name'] for t in o['teachers']]
    course['search_aliases'].extend(a['value'] for t in o['teachers'] for a in t.get('aliases', []) if a.get('kind') in ('teacher_full_pinyin', 'teacher_initials'))
    course['offerings'].append({'term': o['term'], 'department': '大数据学院', 'section_code': o['section_code'], 'lesson_id': o['offering_id'], 'teachers': people, 'credits': (raw.get('course') or {}).get('credits'), 'course_type': (raw.get('courseType') or {}).get('nameZh'), 'student_count': raw.get('stdCount'), 'capacity': None, 'selection_restrictions': clean(raw.get('selectionLimit')), 'syllabus_status':'尚未取得'})
    er = enrollment.get((o['semester_id'], o['offering_id']))
    if er and er.get('code') == o['section_code'] and (er.get('course') or {}).get('code') == o['course_code'] and set(er.get('teachers', [])) == set(people):
        capacity = er.get('limitCount')
        if isinstance(capacity, (int, float)) and not isinstance(capacity, bool):
            course['offerings'][-1].update({'student_count':er.get('stdCount'), 'capacity':capacity, 'enrollment_snapshot_at':er.get('snapshot_at')})
    path = ROOT / 'outlines_live' / (str(o['offering_id']) + '.json')
    if not path.exists():
        path = PRIVATE / '教务大纲/已取大纲' / (str(o['offering_id']) + '.json')
    if path.exists():
        d = read(path); paras = (d.get('model', {}).get('structuredDocument') or {}).get('paragraphs', [])
        paragraphs = [{'heading': clean(p.get('titleZh')), 'content': clean(p.get('contentZh'))} for p in paras if p.get('contentZh')]
        assessment = [{'heading': '考核方式', 'content': '；'.join(str(x.get('criteria', x.get('nameZh', ''))) + ' ' + str(x.get('percentage', '')) + '%' + ('（' + clean(x.get('standard')) + '）' if x.get('standard') else '') for x in d.get('examGradeList', []))}]
        if paragraphs or any(x['content'].strip() for x in assessment):
            course['offerings'][-1]['syllabus_status'] = '已取得正文'
            course['syllabi'].append({'label': o['term'] + ' ' + o['section_code'] + ' ' + '、'.join(people), 'source': '复旦官方教务系统', 'source_url': 'https://fdjwgl.fudan.edu.cn/student/for-std/lesson-search/teachingSyllabusInfo/' + str(o['offering_id']), 'lesson_id': o['offering_id'], 'paragraphs': paragraphs + [x for x in assessment if x['content'].strip()], 'assessment': [{k:clean(str(x.get(k) or '')) for k in ('criteria', 'standard')} | {'percentage':x.get('percentage')} for x in d.get('examGradeList', [])]})

materials_path = HERE / 'material_index.json'
if materials_path.exists():
    for m in read(materials_path).get('records', []):
        if m.get('course_code') in bycode:
            bycode[m['course_code']]['materials'].append({k:v for k,v in m.items() if k not in ('files', 'course_code')})

plan_refs_path = ROOT / 'plans_2026/plan_refs_by_code.json'
if plan_refs_path.exists():
    refs = read(plan_refs_path)
    refs = refs.get('courses_by_code', refs.get('courses', refs.get('by_code', refs))) if isinstance(refs, dict) else {}
    for code, items in refs.items():
        if isinstance(items, dict): items = items.get('plan_refs', [])
        if code in bycode and isinstance(items, list):
            bycode[code]['plan_refs'] = items

review_sources = HERE / 'review_sources.json'
if review_sources.exists():
    for r in read(review_sources).get('records', []):
        if r.get('course_code') in bycode:
            bycode[r['course_code']]['reviews'].append(r)

# Reviewed supplemental files, when provided, contain only course-level fields.
supplement = ROOT / 'reviewed_supplement.json'
if supplement.exists():
    d = read(supplement)
    for code, patch in d.get('courses', {}).items():
        if code not in bycode:
            continue
        for key in ('plan_refs', 'syllabi', 'materials', 'reviews'):
            bycode[code][key].extend(patch.get(key, []))
        if patch.get('synthesis'):
            bycode[code]['synthesis'] = patch['synthesis']

for course in bycode.values():
    course['search_aliases'] = sorted(set(course['search_aliases']))
data = {'department': '大数据学院', 'public_plan_name': '2026级 公共方案', 'scope': '2025秋、2026春大数据学院开课教学班', 'courses': sorted(bycode.values(), key=lambda c: (c['code'], c['name']))}
(HERE / 'dataset.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
print('courses', len(bycode), 'sections', sum(len(c['offerings']) for c in bycode.values()), 'syllabus sections', sum(len(c['syllabi']) for c in bycode.values()))
