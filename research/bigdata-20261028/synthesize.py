"""Summarize factual syllabus requirements, then apply reviewed student comparisons."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'dataset.json'
data = json.loads(path.read_text(encoding='utf8'))

def shorten_intro(text):
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[。！？])', text)
    out = ''
    for sentence in sentences:
        if not sentence.strip(): continue
        if out and len(out) + len(sentence) > 230: break
        out += sentence
        if len(out) >= 180: break
    return out.rstrip('。.!?；;') + '。' if out else ''

custom = {
    'CS20018': '梁家卿班以实验和考试结合理解计算机系统。当前大纲为作业/实验50%、闭卷期末40%、出勤10%。',
    'MATH10003': '邵美悦班衔接基础线性代数与矩阵论，为数值算法和最优化打基础。两学期大纲考核一致：作业10%、期中30%、闭卷期末60%。',
    'MATH20008': '普通版学习凸性、优化模型、KKT条件、拉格朗日对偶与优化算法。作业20%、期中35%、闭卷期末45%。',
    'MATH20008h': '荣誉版以无约束和有约束非线性优化的理论与算法为主，作业40%、闭卷期末60%，优秀率比例不限。',
    'STAT20011': '吴波班的概率论基础大纲为出勤5%、作业25%、闭卷期末70%，期末考试占比较高。',
    'PHIL50006': '由哲学、计算机与公共治理方向教师联合授课，讨论隐私、算法歧视、透明性和AI治理。两个平行班大纲不同：.01班为出勤10%、作业15%、研讨15%、期末论文60%；.02班为课堂表现50%、期末论文50%。',
    'STAT40005': '本次毕业论文共有33个教学班，仅STAT40005.001班成功返回大纲，列出的考核为论文答辩100%。其余32个班次的大纲页面返回HTTP 500；该比例只对应已取得大纲的001班。',
    'CS20017': '黄增峰班围绕基本数据结构与算法设计、分析、实现展开。本次大纲为作业10%、期中闭卷30%、期末闭卷60%，考试占比较高。',
    'CS20017h': '荣誉版在基本数据结构、算法设计与分析之外增加领域前沿内容。大纲为作业10%、期中闭卷30%、期末闭卷60%；优秀率比例不限，考试要求仍按本班大纲执行。',
    'CS40008': '周宝健班把NLP基础、Transformer和大模型后训练与项目实践结合。四次大作业占45%，项目汇报占45%，出勤与课堂表现各5%；作业迟交一天扣该次30分。课堂还有5次、每次20分钟的Quiz。适合愿意持续编程、做模型实验和写项目报告的学生。',
    'STAT50033': '按教学目标和周次表，课程围绕测度概率、渐近理论、充分性与完备性、U统计量、估计、检验和置信集展开，参考教材为Jun Shao的Mathematical Statistics。作业40%、课题论文30%、期末考核30%。大纲的中英文课程简介误写为算法设计内容，与后续目标和进度不一致。',
    'STAT40016': '课程训练统计专业英语的读、写、译能力，覆盖抽样、估计、方差分析和回归。出勤40%、期末论文60%；期末提交不少于5页的英文research proposal，以PDF上传elearning，大纲明确禁止抄袭或使用AI生成论文。',
    'STAT40008': '课程以Hilbert空间方法研究时间序列与空间统计，理论推导较多。课堂表现5%、四次作业25%、期中30%、闭卷期末40%。每次作业基础20分，另有书写工整、LaTeX和附加题共5分加分项；适合愿意持续做理论作业的学生。',
    'STAT50026': '课程结合潜在结果、因果图、随机实验、匹配和逆概率加权等方法，并用R演示社科、公共卫生案例。三次作业共30%、期中25%、论文解读小组汇报20%、期末25%。简介称期末开卷，考核表则写“其他/论文”，应在开课时确认最终形式。',
}

student = json.loads((ROOT / 'student_syntheses.json').read_text(encoding='utf8')) if (ROOT / 'student_syntheses.json').exists() else {}
for c in data['courses']:
    if c['code'] in custom:
        base = custom[c['code']]
    elif c.get('syllabi'):
        doc = c['syllabi'][0]
        descriptions = [p['content'] for p in doc['paragraphs'] if p.get('heading') in ('课程简介（中文）', '课程简介') and len(p.get('content', '')) > 35]
        if not descriptions:
            descriptions = [p['content'] for p in doc['paragraphs'] if p.get('heading') == '教学目标' and len(p.get('content', '')) > 35]
        intro = shorten_intro(descriptions[0]) if descriptions else ''
        weights = []
        for a in doc.get('assessment', []):
            criterion = re.sub(r'[A-Za-z][A-Za-z ()-]*', '', a.get('criteria', '')).strip()
            value = a.get('percentage')
            weights.append(criterion + (f'{float(value):g}%' if value is not None else ''))
        base = intro + ('本次大纲考核为' + '、'.join(weights) + '。' if weights else '')
        if len(c['syllabi']) > 1:
            base += '不同班次的大纲与考核细节见上方对应条目。'
    else:
        base = '本次已核对开课班次、学分、教师与人数快照，教务页面未能取得大纲正文。'
    addition = student.get(c['code'], '')
    if isinstance(addition, dict): addition = addition.get('text', '')
    c['synthesis'] = base + (' ' + addition if addition else '')
    c['card_summary'] = shorten_intro(base if c['code'] in ('PHIL50006', 'STAT40005') else (addition or base))
    c['synthesis_review_ids'] = student.get(c['code'], {}).get('source_ids', []) if isinstance(student.get(c['code'], {}), dict) else []
path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
print('Synthesized', len(data['courses']), 'course descriptions')
