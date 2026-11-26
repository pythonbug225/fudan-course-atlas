"""Build cohort-isolated graphs from official Fudan plan snapshots (stdlib only).

Run: python scripts/build_graphs.py [2023 2024 2025]
No network requests. Name-derived sequences never become official prerequisites.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://github.com/pythonbug225/fudan-course-atlas/blob/foreign-languages-2026-plans-2025fall-2026spring-reviews/research/contributions/foreign-languages-20261028/cohorts-2023-2025/cohorts/'
TOPICS = {
    '英语': ['英语', '英美', '英国', '美国', '莎士比亚'],
    '日语': ['日语', '日本'], '德语': ['德语', '德国', '德奥', '日耳曼'],
    '法语': ['法语', '法国'], '俄语': ['俄语', '俄罗斯'],
    '韩语与韩国语': ['韩语', '韩国语', '韩国', '朝鲜'],
    '西班牙语': ['西班牙语', '西班牙', '拉丁美洲'],
    '语言学': ['语言学', '语音', '语法', '词汇', '语义', '句法', '语料库'],
    '翻译': ['翻译', '笔译', '口译', '英译', '对译', '译后'],
    '文学与文本': ['文学', '小说', '诗歌', '戏剧', '叙事', '文本'],
    '跨文化与区域研究': ['跨文化', '文化史', '国别', '区域研究', '文化交流'],
    '表达与写作': ['写作', '演讲', '辩论', '会话', '修辞'],
    '数字技术': ['人工智能', '编程', '计算机', '数字', '机器学习', '语料库'],
}
PRE_FIELDS = {'defaultPreCourses', 'defaultPreCourseList'}
PRE_TEXT = re.compile(r'先修|前置课程|prerequisit', re.I)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8', newline='\n')


def csvout(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n', extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items() if k in fields})


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def pointer_component(s):
    return str(s).replace('~', '~0').replace('/', '~1')


def walk(value, pointer=''):
    yield pointer, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from walk(v, pointer + '/' + pointer_component(k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from walk(v, pointer + '/' + str(i))


def plain(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', value))).strip()


def sequence(name):
    s = unicodedata.normalize('NFKC', name).replace(' ', '')
    # Preserve the exact series name; changing 初级/中级/高级 is not enough evidence.
    part = 0
    match = re.search(r'\(?([上中下])\)?$', s)
    if match:
        part = {'上': 1, '中': 2, '下': 3}[match[1]]
        s = s[:match.start()]
    level = 0
    match = re.search(r'\(?(IV|III|II|I|[1-4])\)?$', s)
    if match:
        level = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, '1': 1, '2': 2, '3': 3, '4': 4}[match[1]]
        s = s[:match.start()]
    else:
        # Chinese numerals are recognized only as an explicit parenthesized suffix.
        match = re.search(r'\(([一二三四])\)$', s)
        if match:
            level = {'一': 1, '二': 2, '三': 3, '四': 4}[match[1]]
            s = s[:match.start()]
    s = s.strip()
    if not (part or level) or len(s) < 3 or not re.search(r'[\u4e00-\u9fff]', s):
        return None
    return s, (level, part)


def consecutive(a, b, orders):
    if a[0] == b[0]:
        if (a[0], 2) in orders:
            return (a[1], b[1]) in {(1, 2), (2, 3)}
        return (a[1], b[1]) == (1, 3)
    if b[0] != a[0] + 1:
        return False
    return (a[1], b[1]) in {(0, 0), (3, 1)}


def build(year):
    target = ROOT / 'cohorts' / str(year)
    official = target / 'official'
    manifest = official / 'programmes.json'
    if not manifest.exists():
        manifest = official / 'programs.json'
    programs = load(manifest)
    if isinstance(programs, dict):
        programs = programs.get('programs', programs.get('plans'))
    assert isinstance(programs, list) and programs, manifest
    supplemental_path = official / 'supplemental-programmes.json'
    if supplemental_path.exists():
        programs.extend(dict(meta, _supplemental=True, _record_index=i) for i, meta in enumerate(load(supplemental_path)))
    nodes, edges, course_rows, module_rows = {}, {}, [], []
    catalog, audit, plan_courses, node_evidence = [], [], collections.defaultdict(set), collections.defaultdict(list)

    def add_edge(source, dest, kind, label, basis, evidence, pids):
        if source == dest:
            return
        key = (source, dest, kind)
        edge = edges.setdefault(key, {'source': source, 'target': dest, 'type': kind, 'label': label, 'basis': basis, 'source_url': evidence[0]['source_url'], 'program_ids': [], 'evidence': []})
        for pid in pids:
            if pid not in edge['program_ids']:
                edge['program_ids'].append(pid)
        for ev in evidence:
            if ev not in edge['evidence']:
                edge['evidence'].append(ev)

    for meta in programs:
        supplemental = meta.get('_supplemental', False)
        pid = str(meta.get('plan_id', meta.get('id')))
        title = meta.get('title', meta.get('name'))
        raw = supplemental_path if supplemental else next((p for p in [official / 'raw' / f'plan-{pid}.json.gz', official / 'raw' / f'plan-{pid}.json'] if p.exists()), None)
        assert raw, f'Missing source {pid}'
        if supplemental:
            # This normalized extraction is an authored transcription; it is never called raw API data.
            document = {'model': {'id': pid, 'grade': str(year), 'nameZh': title}, 'courseModules': []}
            for module in meta['modules']:
                document['courseModules'].append({'id': module['id'], 'nameZh': module['name'], 'parentAssoc': module.get('parent_id'), 'planCourses': [
                    {'id': f'{module["id"]}:{j}', 'course': {'id': c.get('course_id'), 'code': c.get('code'), 'nameZh': c['name'], 'nameEn': c.get('name_en'), 'credits': c.get('credits')}, 'compulsory': c.get('compulsory'), 'termsText': c.get('terms_text'), 'remark': c.get('remark'), '_source_locator': c.get('source_locator', meta.get('source_note')), 'openDepartment': {'nameZh': c.get('open_department')}} for j, c in enumerate(module['courses'])]})
        else:
            document = load(raw)
        model = document['model']
        assert str(model['id']) == pid and str(model['grade']) == str(year), (pid, model.get('grade'))
        title = title or model['nameZh']
        source_path = raw.relative_to(target).as_posix()
        source_url = meta.get('source_url') or meta.get('detail_url', f'https://fdjwgl.fudan.edu.cn/manager/bizType/2/major-program-search/info/{pid}?skipAuth=1')
        catalog.append({'id': pid, 'title': title, 'source_url': source_url, 'source_path': source_path, 'source_type': 'official_pdf_transcription' if supplemental else 'official_api', 'source_note': meta.get('source_note', ''), 'word_path': None if supplemental else 'official/' + meta.get('word_path', f'word-originals/plan-{pid}.docx').replace('\\', '/'), 'document_path': meta.get('source_path') if supplemental else None})
        pa = {'program_id': pid, 'title': title, 'source_path': source_path, 'source_type': catalog[-1]['source_type'], 'source_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(), 'prerequisite_fields': [], 'prerequisite_text_hits': [], 'course_objects_total': 0, 'course_objects_with_prerequisite_fields': 0, 'course_objects_without_prerequisite_fields': 0, 'word_text_hits': [], 'word_images': []}
        if supplemental:
            pa['review_note'] = meta.get('source_note', '') + '；PDF抄录数据没有 API 先修字段，不能纳入空字段统计；正文及图像核查见独立来源核查。'
        for ptr, obj in ([] if supplemental else walk(document)):
            if isinstance(obj, dict):
                for k in PRE_FIELDS:
                    if k in obj:
                        value = obj[k]
                        pa['prerequisite_fields'].append({'json_pointer': ptr + '/' + k, 'empty': value in (None, [], {}, ''), 'value': value})
                if ptr.endswith('/course') and obj.get('id') is not None:
                    pa['course_objects_total'] += 1
                    fieldkey = 'course_objects_with_prerequisite_fields' if PRE_FIELDS.intersection(obj) else 'course_objects_without_prerequisite_fields'
                    pa[fieldkey] += 1
            elif isinstance(obj, str) and PRE_TEXT.search(obj):
                pa['prerequisite_text_hits'].append({'json_pointer': ptr, 'text': plain(obj)})
        word = target / catalog[-1]['word_path'] if not supplemental else None
        if word and word.exists():
            with zipfile.ZipFile(word) as archive:
                tree = ET.fromstring(archive.read('word/document.xml'))
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                for i, para in enumerate(tree.findall('.//w:p', ns)):
                    text = ''.join(t.text or '' for t in para.findall('.//w:t', ns))
                    if PRE_TEXT.search(text):
                        pa['word_text_hits'].append({'paragraph_index': i, 'text': text})
                pa['word_images'] = [{'member': n, 'sha256': hashlib.sha256(archive.read(n)).hexdigest()} for n in archive.namelist() if n.startswith('word/media/')]
        elif not supplemental:
            raise AssertionError(f'Missing Word original {word}')
        audit.append(pa)
        modules = document.get('courseModules', [])
        known_modules = {}
        module_frequencies = collections.Counter(str(m.get('id', f'index-{i}')) for i, m in enumerate(modules))
        pa['duplicate_module_source_ids'] = {mid: count for mid, count in module_frequencies.items() if count > 1}
        for i, module in enumerate(modules):
            source_mid = str(module.get('id', f'index-{i}'))
            mid = f'{source_mid}:instance-{i}' if module_frequencies[source_mid] > 1 else source_mid
            known_modules[mid] = module
        def module_path(mid):
            parts, seen = [], set()
            while mid in known_modules and mid not in seen:
                seen.add(mid)
                ancestor = known_modules[mid]
                label = ancestor.get('nameZh') or (ancestor.get('type') or {}).get('nameZh')
                if label:
                    parts.append(label)
                mid = str(ancestor.get('parentAssoc'))
            return ' / '.join(reversed(parts))
        for i, module in enumerate(modules):
            source_mid = str(module.get('id', f'index-{i}'))
            mid = f'{source_mid}:instance-{i}' if module_frequencies[source_mid] > 1 else source_mid
            mname = module.get('nameZh') or (module.get('type') or {}).get('nameZh') or ('培养方案根模块' if not module.get('parentAssoc') else '未命名模块')
            mnode = f'module:{pid}:{mid}'
            ptr = f'/{meta["_record_index"]}/modules/{i}' if supplemental else f'/courseModules/{i}'
            module_rows.append({'program_id': pid, 'program': title, 'module_id': mid, 'module_source_id': source_mid, 'module': mname, 'module_path': module_path(mid), 'module_id_origin': 'transcription' if supplemental else 'official_api_with_occurrence_disambiguation' if module_frequencies[source_mid] > 1 else 'official_api', 'parent_module_id': module.get('parentAssoc'), 'required_credits': (module.get('requireInfo') or {}).get('requiredCredits'), 'required_courses': (module.get('requireInfo') or {}).get('requiredCourseNum'), 'require_all': (module.get('requireInfo') or {}).get('requireAll'), 'remark': module.get('remark'), 'source_path': source_path, 'json_pointer': ptr, 'source_url': source_url})
            # RealPlanCourses commonly duplicates planCourses; use the union by plan-course ID.
            seen = set()
            for array_name in ('planCourses', 'realPlanCourses'):
                for j, pc in enumerate(module.get(array_name) or []):
                    course = pc.get('course') or {}
                    signature = str(pc.get('id')) if pc.get('id') is not None else json.dumps(pc, sort_keys=True)
                    if signature in seen:
                        continue
                    seen.add(signature)
                    code = (course.get('code') or '').strip()
                    cid = code or f'course-id:{course.get("id") or pid + ":" + mid + ":" + str(j)}'
                    name = course.get('nameZh') or course.get('nameEn') or f'未命名课程 {cid}'
                    is_activity = code.isdigit() and isinstance(course.get('id'), int) and course['id'] < 0
                    cptr = f'{ptr}/courses/{j}' if supplemental else f'{ptr}/{array_name}/{j}'
                    evidence = {'program_id': pid, 'source_path': source_path, 'json_pointer': cptr, 'source_url': source_url}
                    if supplemental:
                        evidence.update({'source_locator': pc['_source_locator'], 'document_path': meta['source_path'], 'source_type': 'official_pdf_transcription'})
                    row = {'program_id': pid, 'program': title, 'module_id': mid, 'module': mname, 'plan_course_id': pc.get('id'), 'node_id': cid, 'course_code': code, 'course_id': course.get('id'), 'course_name': name, 'course_name_en': course.get('nameEn'), 'open_department': (pc.get('openDepartment') or {}).get('nameZh'), 'credits': course.get('credits'), 'compulsory': pc.get('compulsory'), 'terms': pc.get('terms'), 'terms_text': pc.get('termsText'), 'suggest_terms_text': pc.get('suggestTermsText'), 'remark': pc.get('remark'), 'course_remark': course.get('remark'), 'source_path': source_path, 'json_pointer': cptr, 'source_url': source_url}
                    course_rows.append(row)
                    row['is_activity'] = is_activity
                    if supplemental:
                        row['source_locator'] = pc['_source_locator']
                        row['document_path'] = meta['source_path']
                    plan_courses[pid].add(cid)
                    node_evidence[(cid, name, pid)].append(evidence)
                    node = nodes.setdefault(cid, {'id': cid, 'name': name, 'kind': 'course', 'code': code, 'names': [], 'departments': [], 'program_ids': [], 'programs': [], 'source_urls': [], 'missing_course_code': not bool(code), 'is_activity': is_activity})
                    for key, value in [('names', name), ('departments', row['open_department']), ('program_ids', pid), ('programs', title), ('source_urls', source_url)]:
                        if value and value not in node[key]:
                            node[key].append(value)
                    nodes.setdefault(mnode, {'id': mnode, 'name': mname, 'module_path': module_path(mid), 'kind': 'module', 'program_id': pid, 'program': title, 'program_ids': [pid], 'module_id': mid, 'module_source_id': source_mid, 'source_url': source_url})
                    provenance = 'PDF抄录模块标识' if supplemental else '官方模块 ID'
                    add_edge(cid, mnode, 'program_module', '官方培养方案模块归属', f'“{title}”将该课程列在“{module_path(mid)}”模块（{provenance} {mid}）。模块归属不等于先修关系。', [evidence], [pid])

    # Each proposed edge must be supported by both title variants in the same plan.
    for pid, course_ids in plan_courses.items():
        families = collections.defaultdict(lambda: collections.defaultdict(dict))
        for cid in sorted(course_ids):
            if nodes[cid]['missing_course_code']:
                continue
            for name in nodes[cid]['names']:
                if (cid, name, pid) not in node_evidence:
                    continue
                series = sequence(name)
                if series:
                    families[series[0]][series[1]][cid] = name
        for family, ordermap in families.items():
            orders = sorted(ordermap)
            for a, b in zip(orders, orders[1:]):
                if not consecutive(a, b, orders):
                    continue
                # Multiple same-title codes in one plan remain ambiguous: do not form a cross-product.
                if len(ordermap[a]) != 1 or len(ordermap[b]) != 1:
                    continue
                ca, na = next(iter(ordermap[a].items()))
                cb, nb = next(iter(ordermap[b].items()))
                prefix_a = re.match('[A-Za-z]+', ca)
                prefix_b = re.match('[A-Za-z]+', cb)
                if not prefix_a or not prefix_b or prefix_a[0] != prefix_b[0]:
                    continue
                ev = [node_evidence[(ca, na, pid)][0], node_evidence[(cb, nb, pid)][0]]
                add_edge(ca, cb, 'suggested_sequence', '建议学习顺序（名称推断）', f'同一培养方案中，“{na}”与“{nb}”具有相同系列名“{family}”及相邻编号／上中下标记。仅推断建议顺序，未经课程大纲证实，不是官方先修要求。', ev, [pid])
    for label, keywords in TOPICS.items():
        members = []
        for cid, node in list(nodes.items()):
            if node['kind'] != 'course':
                continue
            matches = [(name, word) for name in node['names'] for word in keywords if word in name]
            if matches:
                members.append((cid, matches))
        if len(members) < 2:
            continue
        tid = 'topic:' + label
        nodes[tid] = {'id': tid, 'name': label, 'kind': 'topic', 'program_ids': sorted({pid for cid, _ in members for pid in nodes[cid]['program_ids']})}
        for cid, matches in members:
            evidence, pids = [], set()
            for name, word in matches:
                for pid in nodes[cid]['program_ids']:
                    for ev in node_evidence.get((cid, name, pid), [])[:1]:
                        evidence.append(dict(ev, note=f'课程名“{name}”含关键词“{word}”'))
                        pids.add(pid)
            add_edge(cid, tid, 'topic', '内容主题线索（名称关键词）', f'课程名称与“{label}”主题关键词匹配，仅用于内容探索，未逐课核实教学大纲，也不代表内容等同或先修关系。', evidence, sorted(pids))

    manual_path = official / 'manual-relations.json'
    if manual_path.exists():
        for relation in load(manual_path):
            assert relation['source'] in nodes and relation['target'] in nodes
            assert relation['type'] in ('official_prerequisite', 'official_recommendation')
            assert relation['basis'] and relation['evidence'] and relation['program_ids']
            for ev in relation['evidence']:
                assert ev.get('quote') and ev.get('source_locator') and ev.get('source_path') and ev.get('source_url')
            label = '官方建议先修（非强制）' if relation['type'] == 'official_recommendation' else '官方明确先修'
            add_edge(relation['source'], relation['target'], relation['type'], label, relation['basis'], relation['evidence'], relation['program_ids'])
    # Audit outputs preserve every encountered field and all text candidates for review.
    fields = [f for plan in audit for f in plan['prerequisite_fields']]
    nonempty = [f for f in fields if not f['empty']]
    # New structured requirements must be reviewed; fail rather than silently drop them.
    assert not nonempty, 'Nonempty prerequisite fields found; review these before publishing.'
    kinds = collections.Counter(e['type'] for e in edges.values())
    api_count = sum(p['source_type'] == 'official_api' for p in audit)
    pdf_count = len(audit) - api_count
    audit_summary = {'programs_checked': len(audit), 'api_programs_checked': api_count, 'pdf_supplemental_programs': pdf_count, 'prerequisite_field_instances': len(fields), 'nonempty_prerequisite_field_instances': len(nonempty), 'course_object_instances': sum(p['course_objects_total'] for p in audit), 'course_objects_with_prerequisite_fields': sum(p['course_objects_with_prerequisite_fields'] for p in audit), 'course_objects_without_prerequisite_fields': sum(p['course_objects_without_prerequisite_fields'] for p in audit), 'json_text_hits': sum(len(p['prerequisite_text_hits']) for p in audit), 'word_text_hits': sum(len(p['word_text_hits']) for p in audit), 'word_image_instances': sum(len(p['word_images']) for p in audit), 'official_prerequisite_edges': kinds['official_prerequisite'], 'official_recommendation_edges': kinds['official_recommendation'], 'scope_note': '字段实例包含 planCourses 与 realPlanCourses 等重复呈现；不是独立课程数量。缺失字段与空字段分别统计。图片由原件保留，图中空间排布不自动转成先修边。PDF抄录方案不参与API字段数量统计。'}
    field_status = f'{len(fields)} 个先修字段实例均为空' if fields else '未发现 API 先修字段'
    status = f'已核查 {api_count} 份 API 方案的原始 JSON 与 Word 文字；{field_status}，另有 {audit_summary["course_objects_without_prerequisite_fields"]} 个课程对象实例未提供这些字段。空缺字段不能证明课程没有先修要求。'
    if pdf_count:
        status += f'另有 {pdf_count} 个官方 PDF 补充方案记录；其先修文字与图像依据独立人工核查，见来源说明与每条证据。'
    status += f'本版官方强制先修 {kinds["official_prerequisite"]} 条，官方建议先修 {kinds["official_recommendation"]} 条。'
    if audit_summary['json_text_hits'] or audit_summary['word_text_hits']:
        status += '正文中出现先修相关文字，候选全文保留在 prerequisite-audit.json，需依据原文区分一般性说明与具体课程条件。'
    stats = {'programs': len(catalog), 'api_programs': api_count, 'pdf_supplemental_programs': pdf_count, 'courses': sum(n['kind'] == 'course' for n in nodes.values()), 'modules': sum(n['kind'] == 'module' for n in nodes.values()), 'topics': sum(n['kind'] == 'topic' for n in nodes.values()), 'edges': len(edges), 'official_prerequisite': kinds['official_prerequisite'], 'official_recommendation': kinds['official_recommendation'], 'suggested_sequence': kinds['suggested_sequence'], 'program_module': kinds['program_module'], 'topic': kinds['topic'], 'course_membership_rows': len(course_rows)}
    stats['curricular_activities'] = sum(n['kind'] == 'course' and n.get('is_activity', False) for n in nodes.values())
    stats['taught_course_codes'] = stats['courses'] - stats['curricular_activities']
    cautions = ['各年仅使用该级官方培养方案所列课程，含双学位等方案引用的其他院系课程；不混入 2025 秋—2026 春实际开课清单。', '名称编号或上／中／下顺序是推断，不是教务选课限制；正式先修须向具体教学大纲与教务系统确认。', '主题关系是名称关键词线索；模块关系只表示官方方案归类，二者均非先修关系。', '同名不同课号保留为不同节点；同一课号的名称变体保留，建议边须有同方案同名证据。', '课程图无连线或没有官方先修边表示证据不足，不能解释为没有先修。', 'API资料是 2026-11-26 查询到的相应入学年级方案快照；PDF出版原版独立保存。两类来源可能有版本差异，不凭同名覆盖或视作完全相同的历史版本。']
    if stats['curricular_activities']:
        cautions.append(f'本级保留 {stats["curricular_activities"]} 个数字代码且内部 ID 为负的官方培养环节（is_activity=true），例如无学分讨论班与博士开题。这些节点不计入 {stats["taught_course_codes"]} 个常规课程代码，但保留在培养方案、名称查询单和图谱中。')
    result = {'schema': 'fudan-course-atlas.graph.v2', 'cohort': year, 'department': '外国语言文学学院', 'title': f'外国语言文学学院 {year} 级课程关系图谱', 'generated_on': '2026-11-26', 'scope': f'{year} 级外国语言文学学院 {api_count} 份 API 培养方案与 {pdf_count} 个官方 PDF 补充方案记录的列课并集。API历史目录不保证覆盖该年级全部专业；覆盖情况以本批次总说明为准。', 'programs': catalog, 'statistics': stats, 'official_prerequisite_status': status, 'cautions': cautions, 'nodes': sorted(nodes.values(), key=lambda n: (n['kind'], n['id'])), 'edges': sorted(edges.values(), key=lambda e: (e['type'], e['source'], e['target']))}
    put(target / 'data/programs.json', catalog)
    put(target / 'data/program-course-index.json', course_rows)
    csvout(target / 'data/program-course-index.csv', course_rows, list(course_rows[0]) + ['source_locator', 'document_path'])
    csvout(target / 'data/program-modules.csv', module_rows, list(module_rows[0]))
    put(target / 'data/prerequisite-audit.json', {'summary': audit_summary, 'programs': audit})
    (target / 'data/course-names.txt').write_text('\n'.join(sorted({n for node in nodes.values() if node['kind'] == 'course' for n in node['names']})) + '\n', 'utf-8', newline='\n')
    graph_dir = target / 'course-graph'
    put(graph_dir / 'graph.json', result)
    csvout(graph_dir / 'nodes.csv', result['nodes'], ['id', 'name', 'kind', 'code', 'is_activity', 'names', 'departments', 'program_ids', 'programs', 'module_id', 'source_urls', 'missing_course_code'])
    csvout(graph_dir / 'edges.csv', result['edges'], ['source', 'target', 'type', 'label', 'basis', 'source_url', 'program_ids', 'evidence'])
    readme = f'''# 外国语言文学学院 {year} 级课程关系图谱

依据教务系统当前公开的 **{api_count} 份 {year} 级培养方案**及 **{pdf_count} 个官方 PDF 补充方案记录**构建，保留所有方案种类及引用的跨院系课程。API历史目录可能不全；PDF补充范围见本批次总说明。这里的方案数量是来源记录数，不表示有相同数量的专业。

| 项目 | 数量 |
| --- | ---: |
| 课程与培养环节节点（按代码） | {stats['courses']} |
| 其中常规课程代码 | {stats['taught_course_codes']} |
| 其中数字代码培养环节 | {stats['curricular_activities']} |
| 有列课的模块节点 | {stats['modules']} |
| 名称关键词主题 | {stats['topics']} |
| 官方强制先修关系 | {stats['official_prerequisite']} |
| 官方建议先修关系（非强制） | {stats['official_recommendation']} |
| 建议学习顺序（推断） | {stats['suggested_sequence']} |
| 官方模块归属边 | {stats['program_module']} |
| 主题关联边（推断） | {stats['topic']} |

[打开交互图谱](index.html)（下载后可离线打开）；[JSON 数据](graph.json)、[节点表](nodes.csv)、[关系表](edges.csv)供后续检索使用。[课程名称查询单](../data/course-names.txt)每行仅一个名称。

## 先修证据

{status}

完整字段与文本审计见 [prerequisite-audit.json](../data/prerequisite-audit.json)。{audit_summary['word_image_instances']} 个 Word 图片实例保留在原文中，不将图片位置或推荐学期自动解释为先修。若另有人工图像核查结论，以本批次总说明为准。

## 关系如何产生

- `official_prerequisite`：仅接受明确且可定位的官方强制先修证据。
- `official_recommendation`：官方明确建议先修，未声称存在教务强制选课限制。
- `suggested_sequence`：同年、同方案、相同系列名称的相邻编号或上／中／下课程；同系列同阶段有多个课号时不生成不确定的排列。每条保留两端原文定位。
- `program_module`：课程与官方模块的归属，用方案 ID + 模块 ID 区分同名模块。若 API 在一个方案中重复使用虚拟模块 ID，则加原始数组位置后缀区分，`module_source_id`保留原值。API课程列表由 `planCourses` 与 `realPlanCourses` 按计划课程 ID 去重取并集。PDF抄录使用明确标识的合成模块 ID。
- `topic`：名称中的语言、翻译、文学等关键词关联；不是教学大纲已确认的知识依赖。

数据以 `program_id`、原始 JSON 相对路径、JSON Pointer、官方详情链接定位。缺少课号时以课程对象 ID 建立临时稳定节点，不凭名称合并。所有主题与顺序边有适用方案列表。

## 覆盖边界

''' + '\n'.join('- ' + caution for caution in cautions) + '\n\n使用 Python 标准库执行 `python scripts/build_graphs.py` 可从本批原始快照重建三个年级的数据（在本批次根目录运行）。\n'
    (graph_dir / 'README.md').write_text(readme, 'utf-8', newline='\n')
    assert all(e['source'] in nodes and e['target'] in nodes for e in edges.values())
    print(json.dumps({'cohort': year, **stats, 'audit': audit_summary}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    for year in [int(y) for y in sys.argv[1:]] or [2023, 2024, 2025]:
        build(year)
