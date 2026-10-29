"""Validate counts, privacy boundaries, HTML attributes, and search behavior."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / 'dataset.json').read_text(encoding='utf8'))
courses = data['courses']
assert len(courses) == 84
assert len({c['code'] for c in courses}) == 84
assert sum(len(c['offerings']) for c in courses) == 146
assert sum(o['term'] == '2025秋' for c in courses for o in c['offerings']) == 67
assert sum(o['term'] == '2026春' for c in courses for o in c['offerings']) == 79
assert all(c.get('synthesis') for c in courses)
assert sum(o.get('capacity') is not None for c in courses for o in c['offerings']) == 146
assert sum(len(c['syllabi']) for c in courses) == 83
assert sum(bool(c['syllabi']) for c in courses) == 78
assert len({p['plan_name'] for c in courses for p in c.get('plan_refs', [])}) == 8
assert len({(o['term'], o['section_code']) for c in courses for o in c['offerings']}) == 146
for c in courses:
    for doc in c['syllabi']:
        if doc.get('assessment'):
            assert abs(sum(float(a.get('percentage') or 0) for a in doc['assessment']) - 100) < .001

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.cards = []; self.script_sources = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'details' and a.get('class') == 'course': self.cards.append(a)
        if tag == 'script' and a.get('src'): self.script_sources.append(a['src'])

html = (ROOT / '大数据学院课程研究预览.html').read_text(encoding='utf8')
page = Page(); page.feed(html)
assert len(page.cards) == len(courses)
assert not page.script_sources, 'Offline preview must not require external scripts'
assert html.count('<h3>一、大纲</h3>') == len(courses)
assert html.count('<h3>四、综合比较</h3>') == len(courses)
for card, course in zip(page.cards, courses):
    expected = ' '.join([course['code'], course['name'], *course['teachers'], *course.get('search_aliases', [])]).lower()
    assert card['data-search'] == expected
    json.loads(card['data-plans']); json.loads(card['data-types'])
assert all('考试' not in c['data-search'] for c in page.cards), 'Review keywords must not enter search index'
assert any('cs20017' in c['data-search'] and '黄增峰' in c['data-search'] and 'hzf' in c['data-search'] for c in page.cards)
for c in courses:
    for r in c.get('reviews', []):
        assert r.get('source'), 'Each review needs attribution'
        assert not r.get('full_text') or r.get('full_text_verified'), 'Full-text label requires verified complete original'

serialized = json.dumps(data, ensure_ascii=False)
for forbidden in ['wxid_', '@chatroom', 'access_token', 'refresh_token', 'Bearer ', 'sessionid', 'password']:
    assert forbidden not in serialized, 'Private identifier or credential field in public dataset'
assert not re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', serialized)
assert not re.search(r'(?<!\d)1[3-9]\d{9}(?!\d)', serialized)

class Images(HTMLParser):
    def __init__(self): super().__init__(); self.images = []; self.scripts = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img' and a.get('src'): self.images.append(a['src'])
        if tag == 'script': self.scripts.append(a.get('src', 'inline'))

plan_pages = list((ROOT / 'plans').rglob('*.html'))
assert len(plan_pages) == 8
for page_path in plan_pages:
    parser = Images(); parser.feed(page_path.read_text(encoding='utf8'))
    assert not parser.scripts
    for src in parser.images:
        assert not src.startswith(('http:', 'https:', '//'))
        assert (page_path.parent / src).is_file(), (page_path.name, src)

stats = {'courses': len(courses), 'sections': 146, 'syllabus_sections': sum(len(c['syllabi']) for c in courses), 'courses_with_student_experience': sum(any(r.get('is_student_experience') for r in c.get('reviews', [])) for c in courses), 'review_records': sum(len(c.get('reviews', [])) for c in courses), 'full_reviews': len({r['id'] for c in courses for r in c.get('reviews', []) if r.get('id', '').startswith('danxi_review_') and r.get('full_text')}), 'courses_with_student_evaluation': sum(any(r.get('is_student_evaluation') for r in c.get('reviews', [])) for c in courses), 'courses_with_current_teacher_evaluation': sum(any(r.get('is_student_evaluation') and r.get('matches_current_teacher') for r in c.get('reviews', [])) for c in courses), 'full_discussion_sources': len({(str(r.get('source_ids', {}).get('hole_id')), str(r.get('source_ids', {}).get('floor_id'))) for c in courses for r in c.get('reviews', []) if r.get('source_ids', {}).get('floor_id') and r.get('full_text')}), 'checks': ['scope counts', 'unique course codes', 'four sections per card', 'search fields restricted to course and teacher identifiers', 'pinyin initials', 'source attribution', 'full text completeness flags', 'private identifiers and email scan', 'no external script dependency', '146 enrollment capacities', '83 syllabi / 78 courses', 'assessment weights sum to 100', '8 curriculum options', '8 offline curriculum pages and local image links']}
(ROOT / 'verification.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps(stats, ensure_ascii=False))
