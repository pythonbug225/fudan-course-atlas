"""Generate the offline department research preview from reviewed, public-safe data."""
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
e = lambda x: html.escape(str(x if x is not None else ''), quote=True)
data = json.loads((HERE / 'dataset.json').read_text(encoding='utf-8'))
courses = data['courses']

def opts(values):
    return ''.join(f'<option value="{e(x)}">{e(x)}</option>' for x in sorted(values) if x)

def plan_ref(p):
    requirement = '必修' if p.get('compulsory') is True else '选修' if p.get('compulsory') is False else '要求未注明'
    module = ' / '.join(p.get('module_path') or []) or p.get('module_name') or ''
    bits = [p.get('plan_name') or '', module, requirement]
    if p.get('credits') is not None: bits.append(f"{float(p['credits']):g} 学分")
    if p.get('terms_text'): bits.append('建议学期 ' + str(p['terms_text']))
    note = '<p class="pre">备注：' + e(p['remark']) + '</p>' if p.get('remark') else ''
    return '<li>' + e(' · '.join(x for x in bits if x)) + note + '</li>'

plans = {p['plan_name'] for c in courses for p in c.get('plan_refs', []) if p.get('plan_name')}
types = {o.get('course_type') for c in courses for o in c['offerings'] if o.get('course_type')}
prefixes = {''.join(x for x in c['code'] if x.isalpha()).upper().removesuffix('H') for c in courses}
cards = []
for c in courses:
    search = ' '.join([c['code'], c['name'], *c['teachers'], *c.get('search_aliases', [])]).lower()
    plan_names = sorted({p['plan_name'] for p in c.get('plan_refs', []) if p.get('plan_name')})
    type_names = sorted({o['course_type'] for o in c['offerings'] if o.get('course_type')})
    prefix = ''.join(x for x in c['code'] if x.isalpha()).upper().removesuffix('H')
    credits = sorted({format(float(o['credits']), 'g') for o in c['offerings'] if o.get('credits') is not None})
    sections = ''.join(f"<li>{e(o['term'])} · {e(o['section_code'])} · {e('、'.join(o['teachers']) or '教师未提供')} · {e(o.get('credits', '未提供'))} 学分 · {e(o.get('course_type') or '类型未提供')} · 人数快照 {e(o.get('student_count') if o.get('student_count') is not None else '未提供')} / 上限 {e(o.get('capacity') if o.get('capacity') is not None else '未提供')} · {e((o.get('enrollment_snapshot_at') or '')[:10])} · 大纲{e(o.get('syllabus_status', '尚未取得'))}{('<details><summary>限选条件</summary><p class=pre>' + e(o.get('selection_restrictions')) + '</p></details>') if o.get('selection_restrictions') else ''}</li>" for o in c['offerings'])
    refs = ''.join(plan_ref(p) for p in c.get('plan_refs', []))
    syllabi = ''.join('<details><summary>' + '官方教学大纲：' + e(s.get('label', '复旦教务系统')) + '</summary>' + ''.join(f"<h5>{e(p.get('heading'))}</h5><p class='pre'>{e(p.get('content'))}</p>" for p in s.get('paragraphs', []) if p.get('content')) + '</details>' for s in c.get('syllabi', []))
    materials = ''.join(f"<article><a href='{e(m['url'])}' target='_blank' rel='noopener noreferrer'>{e(m['title'])}</a><p>{e(m.get('note', ''))} · 来源：{e(m.get('source', ''))}</p></article>" for m in c.get('materials', []))
    reviews = []
    for r in sorted(c.get('reviews', []), key=lambda r: ('同届' in r.get('kind', ''), bool(r.get('matches_current_teacher')), len(r.get('full_text', ''))), reverse=True):
        original = f"<details><summary>查看{e(r.get('full_text_label', '完整原评'))} · {len(r['full_text'])} 字</summary><p class='pre'>{e(r['full_text'])}</p><small>匿名原作者 · {e(r.get('license', ''))} · {e(r.get('changes', ''))}</small></details>" if r.get('full_text') else ''
        link = f"<p><a href='{e(r['url'])}' target='_blank' rel='noopener noreferrer'>查看公开平台原文</a></p>" if r.get('url') and r.get('platform') in ('知乎', '小红书') else ''
        reviews.append(f"<article><p>{e(r.get('summary'))}</p><small>来源：{e(r.get('source'))} · {e(r.get('teacher') or '教师未确认')} · {e(r.get('term') or '学期未确认')} · {e(r.get('kind', '讨论'))}</small>{original}{link}</article>")
    has_experience = any(r.get('is_student_evaluation') or r.get('is_student_experience') for r in c.get('reviews', []))
    has_current = any(r.get('matches_current_teacher') and (r.get('is_student_evaluation') or r.get('is_student_experience')) for r in c.get('reviews', []))
    flag = ('<span class="missing">暂无当前教师直接评价 · 有历史/课程族记录</span>' if has_experience and not has_current else '') if has_experience else '<span class="missing">暂未收录学生评价</span>'
    honor = '<span class="honor">荣誉课 · 优秀率比例不限</span>' if c.get('honor') else ''
    plan_json = e(json.dumps(plan_names, ensure_ascii=False))
    type_json = e(json.dumps(type_names, ensure_ascii=False))
    cards.append(f'''<details class="course" data-search="{e(search)}" data-plans="{plan_json}" data-types="{type_json}" data-prefix="{e(prefix)}"><summary><strong>{e(c['name'])}</strong><span> {e(c['code'])} · {e('、'.join(c['terms']))}</span><p>{e('、'.join(c['teachers']) or '教师未提供')} · 大数据学院 · {e(' / '.join(credits) if credits else '未提供')} 学分</p>{honor}{flag}<p class="blurb">{e(c.get('card_summary', ''))}</p></summary><div class="inner"><h3>教学班</h3><ul>{sections}</ul><details><summary>培养方案位置</summary><ul>{refs or '<li>本次取得的方案中未找到直接对应课程代码。</li>'}</ul></details><h3>一、大纲</h3>{syllabi or '<p>尚未取得可用大纲。</p>'}<h3>二、课程资料</h3>{materials or '<p>暂未收录已核对的资料。</p>'}<h3>三、学生评价与讨论</h3>{''.join(reviews) or '<p>暂未收录与本课程匹配的学生评价或讨论。</p>'}<h3>四、综合比较</h3><p>{e(c.get('synthesis') or '现有材料不足以比较教学体验；可先参照上方班次及大纲。')}</p></div></details>''')

page = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>大数据学院课程研究预览</title><style>body{font:16px/1.7 system-ui,sans-serif;background:#f5f7f4;color:#203a33;margin:0}main{max-width:1080px;padding:24px;margin:auto}input{width:100%;box-sizing:border-box;padding:14px;border:1px solid #aac1b4;border-radius:10px;font:inherit}.filters{display:flex;gap:12px;flex-wrap:wrap}.filters label{display:flex;flex-direction:column;gap:4px;flex:1 1 200px}select{font:inherit;padding:9px;border:1px solid #aac1b4;border-radius:8px;background:white}.notice,.course{background:white;border:1px solid #d9e2dd;border-radius:12px;padding:18px;margin:14px 0}.notice{border-left:5px solid #387d6d}.course{border-left:5px solid #426f99}.course[data-prefix="STAT"]{border-left-color:#a2763d}.course[data-prefix="MATH"]{border-left-color:#3e8872}.course[data-prefix="CS"]{border-left-color:#6557a9}.course[data-prefix="GEEC"]{border-left-color:#bd8050}.course[data-prefix="GESP"]{border-left-color:#b36577}.course[data-prefix="AIB"],.course[data-prefix="AIS"],.course[data-prefix="AIT"]{border-left-color:#318db0}.course[data-prefix="MF"]{border-left-color:#9b7b32}.honor,.missing{display:inline-block;border-radius:6px;padding:2px 8px;margin-right:8px}.honor{background:#f0e9fa;color:#644396}.missing{background:#f5eee3;color:#725b39}summary{cursor:pointer}.course>summary strong{font-size:21px}.course>summary span,small{color:#607c71}.course>summary p{margin:4px 0}.inner{border-top:1px solid #e6ede8;padding-top:8px}.pre{white-space:pre-wrap;overflow-wrap:anywhere}select{max-width:100%;min-width:0}article{border-left:3px solid #8ab7a0;padding-left:14px}h3{margin-top:25px}a{color:#146b59}</style></head><body><main><h1>大数据学院课程研究预览</h1><div class="notice">范围：2025 秋、2026 春大数据学院实际开课；包含不同层次课程，课程是否属于某个本科方案以方案位置为准。教学班人数为历史快照；来源中的个人体验不等于官方规定。</div><label for="q">搜索课程代码、课程名、教师名或其拼音首字母</label><input id="q" autocomplete="off" placeholder="例如 CS20017、数据结构、教师姓名"><p>选择一个专业方案时，同时显示公共方案中直接对应的课程。</p><div class="filters"><label>培养方案 <select id="plan"><option value="">全部方案</option>__PLANS__</select></label><label>课程类型 <select id="type"><option value="">全部类型</option>__TYPES__</select></label><label>课程代码前缀 <select id="prefix"><option value="">全部前缀</option>__PREFIXES__</select></label></div><p id="count"></p><div id="courses">__CARDS__</div></main><script>const q=document.getElementById('q'),plan=document.getElementById('plan'),type=document.getElementById('type'),prefix=document.getElementById('prefix'),cards=[...document.querySelectorAll('.course')],count=document.getElementById('count');function filter(){let v=q.value.trim().normalize('NFKC').toLowerCase(),n=0;for(const c of cards){let plans=JSON.parse(c.dataset.plans),types=JSON.parse(c.dataset.types),planOk=!plan.value||plans.includes(plan.value)||(plan.value!==__PUBLIC_PLAN__&&plans.includes(__PUBLIC_PLAN__));let ok=(!v||c.dataset.search.normalize('NFKC').toLowerCase().includes(v))&&planOk&&(!type.value||types.includes(type.value))&&(!prefix.value||c.dataset.prefix===prefix.value);c.hidden=!ok;if(ok)n++}count.textContent='显示 '+n+' / '+cards.length+' 门课程'}q.addEventListener('input',filter);for(const x of [plan,type,prefix])x.addEventListener('change',filter);filter();</script></body></html>'''
for key, value in {'__PLANS__': opts(plans), '__TYPES__': opts(types), '__PREFIXES__': opts(prefixes), '__CARDS__': ''.join(cards), '__PUBLIC_PLAN__': json.dumps(data.get('public_plan_name', '2026级 公共方案'), ensure_ascii=False)}.items():
    page = page.replace(key, value)
(HERE / '大数据学院课程研究预览.html').write_text(page, encoding='utf-8')
print(f'Generated {len(cards)} courses')
