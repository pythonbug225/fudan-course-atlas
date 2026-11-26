"""Extract unchanged handbook pages and all 2023 foreign-language plan views.

Usage: python scripts/extract_handbook_2023.py /path/to/official-full-handbook.pdf
Dependencies: pdfplumber and pypdf. No OCR or invented course codes are used.
"""
from pathlib import Path
import copy
import hashlib
import json
import re
import shutil
import sys
import pdfplumber
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'cohorts/2023/official'
URL = 'https://jwc.fudan.edu.cn/_upload/article/files/83/6c/8a3c080c4f8991024f4b59ad4f1b/64d23c13-0465-4619-bd18-9e491594f850.pdf'
# Printed page ranges; body page 1 is physical page 13.
MAJORS = [
    ('english', '英语', 206, 210, 211, 212, 213, 214, False),
    ('translation', '翻译', 215, 218, 219, 220, 221, 222, False),
    ('russian', '俄语', 223, 225, 226, 227, 228, 229, True),
    ('german', '德语', 230, 232, 233, 234, 235, 236, True),
    ('french', '法语', 237, 239, 240, 241, 242, 243, True),
    ('japanese', '日语', 244, 246, 247, 248, 249, 250, False),
    ('korean', '朝鲜语', 251, 253, 254, 255, 256, 257, True),
    ('spanish', '西班牙语', 258, 260, 261, 262, 263, 264, True),
]
CODE = re.compile(r'^[A-Z]{2,8}\d{6}$')

def clean(value):
    return re.sub(r'\s+', '', value or '')

def put(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', 'utf-8', newline='\n')

def main():
    source = Path(sys.argv[1])
    reader = PdfReader(source)
    assert len(reader.pages) == 952, 'Unexpected handbook pagination'
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, OUT / 'full-curriculum-2023-original.pdf')
    for name, start, end in [('handbook-excerpt.pdf', 206, 264), ('handbook-common-reference.pdf', 1, 72)]:
        writer = PdfWriter()
        for number in range(start, end + 1):
            writer.add_page(reader.pages[number + 11])
        writer.add_metadata({'/Title': f'2023官方手册原页摘录：印刷页{start}-{end}', '/Subject': URL, '/Producer': 'pypdf page extraction; source content unchanged'})
        with (OUT / name).open('wb') as f:
            writer.write(f)
    pdf = pdfplumber.open(source)
    raw = []
    tables_by_page = {}
    texts = []
    for printed in range(206, 265):
        page = pdf.pages[printed + 11]
        tables = page.extract_tables()
        tables_by_page[printed] = tables
        text = page.extract_text() or ''
        raw.append({'physical_page': printed + 12, 'printed_page': printed, 'excerpt_page': printed - 205, 'tables': tables})
        texts.append({'physical_page': printed + 12, 'printed_page': printed, 'text': text})
    put(OUT / 'handbook-table-extraction.json', raw)
    put(OUT / 'handbook-page-text.json', texts)
    skipped = []

    def locator(page, table, row):
        return f'原PDF物理页{page + 12}／印刷页{page}；外院摘录第{page - 205}页，第{table + 1}表第{row + 1}行（含表头）'

    def parse(start, end, pid, advice=False):
        modules = {}
        current = ''
        section = ''
        requirement = ''
        for page in range(start, end + 1):
            for ti, table in enumerate(tables_by_page[page]):
                assert len(table[0]) == (17 if advice else 10), (page, len(table[0]))
                for ri, row in enumerate(table):
                    values = [clean(v) for v in row]
                    if not advice:
                        if values[0] == '课程模块':
                            continue
                        if values[0]:
                            current = values[0]
                        name, code, credits, terms = values[1], values[2], values[3], values[8]
                        module = current
                        note = values[9]
                        req = ''
                    else:
                        if values[0] == '分类' or (not values[3] and values[8] == '一'):
                            continue
                        if values[0]:
                            section = values[0]
                        if values[1]:
                            current = values[1]
                            requirement = ''
                        if values[6]:
                            requirement = values[6]
                        name, code, credits = values[3], values[7], values[4]
                        module = '修读建议/' + section + '/' + current
                        terms = '；'.join(f'第{i + 1}学期:{value}周学时' for i, value in enumerate(values[8:16]) if value)
                        note = values[16]
                        req = requirement
                    if not CODE.fullmatch(code):
                        if name:
                            skipped.append({'program_id': pid, 'name': name, 'code_cell': code, 'source_locator': locator(page, ti, ri), 'reason': '非具体课程代码行，可能为模块/可选课程集合/测试或要求；不造课程代码', 'cells': row})
                        continue
                    assert name and module, (page, ri, row)
                    entry = {'code': code, 'name': name, 'credits': credits, 'terms_text': terms, 'source_locator': locator(page, ti, ri)}
                    if req:
                        entry['requirement_text'] = req
                        if req == '必修':
                            entry['compulsory'] = True
                        elif req == '选修':
                            entry['compulsory'] = False
                    if note:
                        entry['remark'] = note
                    item = modules.setdefault(module, {'id': f'{pid}-module-{len(modules) + 1}', 'name': module, 'courses': []})
                    item['courses'].append(entry)
        return list(modules.values())

    plans = []
    audit = []
    for slug, name, start, end, adv_start, adv_end, intl_start, intl_end, missing in MAJORS:
        # Every main table is preserved in raw extraction, including API-covered majors.
        pid = 'pdf-2023-' + slug
        common = parse(start, end, pid)
        variants = [(pid, '', adv_start, adv_end, 'original_handbook_curriculum'),
                    (pid + '-international', '（留学生适用）', intl_start, intl_end, 'international_reading_advice')]
        for vid, suffix, va, vb, kind in variants:
            modules = copy.deepcopy(common)
            for i, module in enumerate(modules):
                module['id'] = f'{vid}-professional-{i + 1}'
            modules.extend(parse(va, vb, vid, advice=True))
            title = f'2023 {name}专业“2+X”教学培养方案及修读建议{suffix}（官方手册）'
            plan = {'plan_id': vid, 'title': title, 'cohort': 2023, 'source_url': URL + f'#page={start + 12}', 'source_path': 'official/handbook-excerpt.pdf', 'source_kind': 'official_handbook_pdf', 'pdf_record_type': kind,
                    'source_note': f'官方2023手册原页摘录；专业课表印刷页{start}-{end}（物理{start + 12}-{end + 12}），对应修读建议印刷页{va}-{vb}（物理{va + 12}-{vb + 12}）。本记录ID为本项目生成的PDF视图ID，非教务系统方案ID。' + ('留学生视图使用该专业通用专业课表与留学生修读建议，未套用普通学生的通识课程要求。' if suffix else ''),
                    'modules': modules}
            plans.append(plan)
            codes = sorted({c['code'] for module in modules for c in module['courses']})
            audit.append({'plan_id': vid, 'title': title, 'module_count': len(modules), 'course_rows': sum(len(m['courses']) for m in modules), 'distinct_codes': len(codes), 'printed_pages': list(range(start, end+1)) + list(range(va, vb+1))})
    put(OUT / 'supplemental-programmes.json', plans)
    put(OUT / 'handbook-non-course-rows.json', skipped)
    hits = [{'physical_page': p['physical_page'], 'printed_page': p['printed_page'], 'text': p['text']} for p in texts if re.search(r'先修|前置|基础上|先选|先修读', p['text'])]
    meta = {'source_url': URL, 'source_original_path': 'full-curriculum-2023-original.pdf', 'retrieved_date': '2026-11-26', 'source_bytes': source.stat().st_size, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'source_physical_pages': len(reader.pages),
            'excerpt_note': '从官方整校PDF无改写抽取原页面，非原站完整文件；原文排版与印刷页码保留。',
            'excerpts': [], 'supplemental_records': audit, 'text_prerequisite_hits': hits,
            'prerequisite_interpretation': '外院章文本未发现可直接落到课程对的正式先修要求。俄语“在选修…基础上，任选10学分”是模块修读学分组合，不据此建立课程对先修。修读建议中的学期排列不自动成为官方先修。',
            'non_course_rows_count': len(skipped), 'common_reference_scope': '通识、专项、大类基础和学生身份要求作为完整参考原件保存，未把全校可选课程自动并入外院必修。只对各专业修读建议表实际列出的具体课程代码建立节点。'}
    for name, start, end in [('handbook-excerpt.pdf',206,264),('handbook-common-reference.pdf',1,72)]:
        path = OUT/name
        extracted = PdfReader(path)
        assert all(p.get_contents().get_data() == reader.pages[n+11].get_contents().get_data() for p,n in zip(extracted.pages,range(start,end+1))), 'Page contents changed'
        meta['excerpts'].append({'path': name, 'printed_page_range': [start,end], 'physical_page_range': [start+12,end+12], 'excerpt_pages': end-start+1, 'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'all_page_content_streams_match_original': True, 'page_mapping': [{'excerpt_page':i-start+1,'printed_page':i,'source_physical_page':i+12}for i in range(start,end+1)]})
    put(OUT/'handbook-source-audit.json',meta)
    print(json.dumps({'supplemental_records':len(plans),'records':audit,'non_course_rows':len(skipped)},ensure_ascii=False))

if __name__ == '__main__':
    main()
