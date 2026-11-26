"""Build a school's cohort graphs offline from Fudan's publicly exported plans.

Usage: python build.py SCHOOL_DIRECTORY [--year YYYY]
Inputs: YYYY/programmes.json, YYYY/raw/plan-ID.json.gz, YYYY/originals/plan-ID.docx
Outputs are deterministic (Python 3.10+) and replaced individually on successful writes.
"""
from __future__ import annotations

import argparse
import collections
import functools
import gzip
import hashlib
import html
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import quote
import xml.etree.ElementTree as ET
import zipfile


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    if path.exists() and path.read_bytes() == data:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        handle.write(data)
        temporary = handle.name
    os.replace(temporary, path)


def encode(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def plain(value):
    text = re.sub(r"</(?:p|div|li|tr)>|<br\s*/?>", "\n", str(value or ""), flags=re.I)
    return html.unescape(re.sub(r"<[^>]*>", " ", text)).strip()


@functools.lru_cache(maxsize=8192)
def norm(text):
    return re.sub(r"[\s\x00-\x1f\x7f]+", "", unicodedata.normalize("NFKC", str(text))).casefold()


def md(value):
    return html.escape(str(value), quote=False).replace("|", "&#124;").replace("\n", " ")


def mermaid_label(name):
    return re.sub(r"[^\w\s\u3400-\u9fff（）()·ⅠⅡⅢⅣⅤ-]", "·", name)[:43]


def number_terms(terms):
    if not isinstance(terms, list) or not terms or not all(re.fullmatch(r"TERM_[1-9]\d?", str(t)) for t in terms):
        return ()
    return tuple(sorted({int(t[5:]) for t in terms}))


def module_title(module):
    return module.get("nameZh") or (module.get("type") or {}).get("nameZh") or "培养方案"


def module_paths(modules):
    by_id = collections.defaultdict(list)
    for m in modules:
        by_id[m.get("id")].append(m)
    output = []
    for m in modules:
        chain = [m]
        seen = {id(m)}
        while len(by_id.get(chain[-1].get("parentAssoc"), [])) == 1:
            parent = by_id[chain[-1]["parentAssoc"]][0]
            if id(parent) in seen:
                break
            seen.add(id(parent))
            chain.append(parent)
        output.append(" / ".join(module_title(item) for item in reversed(chain)))
    return output


LABELS = {
    "official_preparation": "方案列明预修",
    "official_sequence": "方案文字指定顺序",
    "recommended_preparation": "建议学习顺序",
    "term_order": "方案排课先后",
    "content": "课程内容联系",
}

# Match literal course names within a single programme. Sequences express editorial
# study advice; themes describe common subject matter. Never infer credit equivalence.
SEQUENCES = [
    ("微积分", "概率论与数理统计", "积分为连续型随机变量的计算提供基础。"),
    ("概率论", "数理统计", "分布和期望为统计估计与检验提供基础。"),
    ("实变函数", "泛函分析", "测度与积分有助于理解函数空间。"),
    ("高等代数", "抽象代数", "线性空间有助于引入更一般的代数结构。"),
    ("数据结构", "算法设计与分析", "数据组织与基本操作为算法设计提供基础。"),
    ("程序设计基础", "数据结构", "编程基础有助于实现数据结构。"),
    ("机器学习", "深度学习", "学习模型和优化算法可为神经网络学习做准备。"),
    ("电路原理", "模拟电子技术", "电路分析可用于理解模拟电路。"),
    ("信号与系统", "数字信号处理", "系统、变换与采样是数字信号分析的基础。"),
    ("理论力学", "材料力学", "静力学分析有助于理解构件受力。"),
    ("数学物理方法", "量子力学", "数学物理中的微分方程和算子方法可用于量子力学。"),
    ("原子物理学", "量子力学", "原子物理的问题为量子理论提供物理背景。"),
    ("普通化学", "分析化学", "溶液与平衡概念支持化学分析。"),
    ("有机化学", "生物化学", "官能团与有机反应是理解生物分子性质的基础。"),
    ("生物化学", "分子生物学", "生物分子的结构与功能支持分子生物学学习。"),
    ("细胞生物学", "组织学与胚胎学", "细胞结构有助于理解组织层次和发育。"),
    ("系统解剖学", "局部解剖学", "系统解剖中的结构名称与位置用于区域解剖学习。"),
    ("生理学", "病理生理学", "正常生理功能为理解功能异常提供参照。"),
    ("病理学", "诊断学", "组织与器官病变有助于解释临床表现。"),
    ("诊断学", "内科学", "病史采集、体格检查与诊断推理可用于内科病例学习。"),
    ("诊断学", "外科学", "诊断推理和临床检查可为外科课程作准备。"),
    ("医学统计学", "流行病学", "统计推断支持群体健康研究。"),
    ("基础护理学", "内科护理学", "一般护理评估为专科护理作准备。"),
    ("微观经济学", "产业经济学", "企业和市场结构是产业经济分析的基础。"),
    ("统计学", "计量经济学", "统计推断为计量模型的估计与检验提供基础。"),
    ("会计学原理", "财务管理", "会计报表有助于理解财务决策。"),
    ("管理学原理", "组织行为学", "组织与管理基本概念有助于组织行为分析。"),
    ("法理学", "宪法学", "法的概念与规范体系可用于理解宪法制度。"),
    ("政治学原理", "比较政治学", "制度与权力的基本概念可用于比较分析。"),
    ("社会学概论", "社会学理论", "社会学概念有助于阅读理论文献。"),
    ("社会研究方法", "社会调查方法", "研究设计的基础可用于调查方案设计。"),
    ("语言学概论", "社会语言学", "语言结构与语言变异概念可支持社会语言学学习。"),
    ("古代汉语", "古典文献学", "古汉语阅读可用于整理和解读古典文献。"),
    ("史学概论", "史学史", "史学的概念与方法有助于理解史学发展。"),
    ("新闻学概论", "新闻采访", "新闻生产与新闻价值的基础概念可用于采访。"),
    ("传播学概论", "传播研究方法", "传播模型可为研究问题和设计提供基础。"),
    ("考古学概论", "田野考古学", "考古材料与研究方法的基础可用于田野课程。"),
    ("博物馆学概论", "博物馆陈列设计", "藏品、受众与博物馆职能为陈列设计提供背景。"),
]

THEMES = [
    ("数学模型", "最优化方法", "模型目标、决策变量与优化求解"),
    ("概率论", "随机过程", "随机现象与概率模型"),
    ("理论力学", "流体力学", "运动与守恒关系"),
    ("电动力学", "光学", "电磁波传播"),
    ("物理化学", "化工原理", "热力学与物质传递"),
    ("材料科学基础", "材料分析方法", "材料结构与表征"),
    ("半导体物理", "半导体器件", "载流子行为与器件性质"),
    ("操作系统", "计算机组成原理", "计算机资源与硬件接口"),
    ("离散数学", "数据结构", "图、树与离散结构"),
    ("生理学", "药理学", "生理调节与药物作用"),
    ("药剂学", "药物分析", "药物制剂与质量评价"),
    ("免疫学", "病理学", "炎症反应与组织变化"),
    ("儿科学", "妇产科学", "围产期与儿童早期健康"),
    ("护理研究", "医学统计学", "护理数据与统计推断"),
    ("卫生统计学", "流行病学", "群体健康数据与疾病分布"),
    ("经济学原理", "管理学原理", "组织决策与资源配置"),
    ("宏观经济学", "货币银行学", "货币政策与宏观经济运行"),
    ("国际政治学", "国际关系理论", "国际体系与国家间关系"),
    ("民法学", "民事诉讼法学", "民事权益与司法救济"),
    ("刑法学", "刑事诉讼法学", "犯罪认定与诉讼程序"),
    ("伦理学", "政治哲学", "规范、正义与公共判断"),
    ("中国古代文学", "古代汉语", "古典文本及其语言背景"),
    ("现代汉语", "语言学概论", "语言结构和语法分析"),
    ("中国古代史", "中国历史地理", "中国历史进程与空间变化"),
    ("文化人类学", "社会学概论", "社会组织与文化实践"),
    ("广告学概论", "传播学概论", "媒介传播与受众"),
]

# Keywords name a particular subject, authoring method or object. Membership
# comes directly from the two course titles; shared strings alone never create
# a prerequisite. Limit links per subject to keep very large catalogues usable.
TOPICS = """音韵 方言 语音 文字学 训诂 语义 语用 语法 写作 翻译 口译 笔译 文学史
古代文学 现代文学 戏剧 诗歌 小说 英美文学 英语文学 中国史 世界史 档案 考古 博物馆
文物 文化遗产 遗产保护 旅游管理 旅游市场 酒店管理 体育训练 体育竞赛 运动生理 运动康复
体育科研 社会调查 统计学 社会学 人类学 社会政策 社会工作 社会保障 传播 新闻 广告
媒介 公共关系 国际关系 公共政策 政治制度 政治哲学 马克思主义 伦理学 逻辑学 科学哲学
刑法 民法 宪法 诉讼 知识产权 国际法 国际经济 国际贸易 投资 金融 计量经济 会计
市场营销 供应链 审计 风险管理 证券 公司治理 计量方法 环境科学 环境工程 污染控制
光学 纳米材料 材料物理 聚合物 高分子 电化学 无机化学 分析化学 有机化学 物理化学
集成电路 微电子 半导体 电磁 信号处理 数字电路 模拟电路 通信系统 自动控制 机器人
材料力学 有限元 工程热力学 流体力学 空气动力学 凝聚态 量子 统计物理 天体物理
气象 气候 海洋 地球物理 核物理 辐射测量 放射防护 线性代数 实变函数 偏微分方程
数值分析 随机过程 机器学习 数据库 数据结构 人机交互 计算机视觉 图像处理 数字媒体
数据科学 人工智能 生物医学工程 医学影像 临床医学 临床诊断 解剖 组织胚胎 生理学
儿科 内科 外科 口腔 护理 药剂 药理 药物分析 临床药学 药事管理 病理 医学伦理
流行病学 卫生统计 公共卫生 职业卫生 环境卫生 健康教育 健康管理 法医学 法医临床
生态学 植物学 动物学 遗传学 生物化学 细胞生物学 分子生物学 生物信息学""".split()


def literal_topic_links(placements, unique, add, prepare):
    seen_names = {r["name"] for items in placements.values() for r in items if not r["public_reference"]}
    for tag in TOPICS:
        hits = sorted((name for name in seen_names if tag in name and unique(name)), key=lambda v: (len(v), v))
        if len(hits) < 2:
            continue
        # Use a short topic-defining title as hub, while retaining each source code.
        hub = hits[0]
        for name in hits[1:5]:
            if unique(hub) == unique(name):
                continue
            add(unique(hub), unique(name), "content", f"本方案两门课程的题名均含“{tag}”，可据此对照这一主题。")
            base = norm(hub)
            if base in {norm(tag + suffix) for suffix in ["基础", "概论", "导论", "原理", "入门"]} and base != norm(name):
                prepare(unique(hub), unique(name), f"“{hub}”题名标明基础层次，前置阅读可帮助了解“{name}”中的{tag}主题。")

# Derive content links for a theory course and the experiment/practice course of the
# same name. Polarity (A, B, H), course level, and any subject identifiers are retained.
PRACTICE = re.compile(r"^(.*?)(?:\((?:实验|实践|实习)\)|(?:实验|实践|实习)(?:课)?)$")
ORDINAL = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6,
           "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
           "上": 1, "中": 2, "下": 3, "1": 1, "2": 2, "3": 3, "4": 4}
SERIES = re.compile(r"^(.+?)(?:\(([一二三四五六上中下1-4]|iv|vi|iii|ii|i|v)\)|([一二三四五六上下中]|iii|ii|iv|vi|i|v))((?:\(h\)|荣誉)?)$")
KEYWORD = re.compile(r"先修|预修|前置课程|前序课程|前续课程|先行课程|修读顺序|修完.{0,35}后方可")
PRE_FIELD = re.compile(r"prerequi|pre.?course", re.I)
FORMS = re.compile(r"^\s*(?:本课程的?|本课的?)?(?:先修(?:课程|要求)?|预修(?:课程|要求)?|前置课程|前序课程|先行课程)\s*(?:为|是|包括|[:：])\s*(.+?)\s*[。.]?$")
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def title_series(title):
    match = SERIES.fullmatch(norm(title))
    if not match:
        return None
    stem, bracketed, bare, honor = match.groups()
    if len(stem) < 2:
        return None
    token = bracketed or bare
    # A suffix in an English word (e.g. 'Hawaii') is not a course ordinal.
    if not bracketed and token.isascii() and stem[-1].isascii() and stem[-1].isalpha():
        # A course band on a Chinese title, e.g. 数学分析AI.
        if not (stem[-1] in "abcd" and len(stem) > 1 and not stem[-2].isascii()):
            return None
    # Bare Chinese numerals occur in names (e.g. 统一). Require parentheses for them.
    if not bracketed and token in "一二三四五六":
        return None
    family = "parts" if token in "上中下" else "number"
    return (stem, honor, family), ORDINAL[token]


def split_sources(text):
    return [norm(x).strip("《》〈〉“”\"' ") for x in re.split(r"[、,，;；]", text)]


def collect_clauses(value, route, output):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"model", "document", "courseModules"} and route == "":
                continue
            collect_clauses(child, f"{route}/{key}", output)
    elif isinstance(value, list):
        for i, child in enumerate(value):
            collect_clauses(child, f"{route}/{i}", output)
    elif isinstance(value, str) and KEYWORD.search(value):
        output.extend((route, s.strip()) for s in re.split(r"[。；\n]", plain(value)) if KEYWORD.search(s))


def build_plan(year_dir, meta, courses, rows, modules_out):
    pid = str(meta["id"])
    raw_path = year_dir / "raw" / f"plan-{pid}.json.gz"
    doc_path = year_dir / "originals" / f"plan-{pid}.docx"
    raw_bytes = raw_path.read_bytes()
    detail = json.loads(gzip.decompress(raw_bytes))
    model = detail["model"]
    check(str(model["grade"]) == year_dir.name and str(model["id"]) == pid, f"{raw_path}: model identity")
    modules = detail.get("courseModules") or []
    paths = module_paths(modules)
    by_name = collections.defaultdict(set)
    placements = collections.defaultdict(list)
    member_courses = collections.defaultdict(set)
    clauses, contextual, sequences = [], [], []
    collect_clauses(detail, "", clauses)
    # Some API generations supply just document.paragraphs.
    if not detail.get("programContent"):
        collect_clauses(detail.get("document"), "/document", clauses)
    for mi, module in enumerate(modules):
        loc = f"/courseModules/{mi}"
        module_rows = module.get("planCourses") or []
        # Scope is intentionally narrow: only label public options when the module
        # itself references a public/general-education catalogue.
        public = bool(module.get("reference") and re.search("通识|大学英语|公共体育", paths[mi]))
        modules_out.append({"plan": pid, "index": mi, "path": paths[mi], "reference": bool(module.get("reference")),
                            "rules": module.get("requireInfo"), "limit": module.get("limitInfo"),
                            "wording": [v for v in (module.get("labelText"), module.get("remark"), module.get("commentText")) if v]})
        for k in ["remark", "labelText", "commentText"]:
            collect_clauses(module.get(k), f"{loc}/{k}", clauses)
            note = plain(module.get(k))
            # The full module note also describes a separate honors alternative.
            # Record only the ordinary route as an ordered pair, preserving the
            # complete statement as evidence so readers can recover its exceptions.
            ordinary = re.search(r'一般修读顺序[：:]\s*[“《]([^”》]+)[”》][^；。]{0,24}大一上学期必修[，,]\s*[“《]([^”》]+)[”》][^；。]{0,24}大一下学期必修', note)
            if ordinary:
                sequences.append((ordinary[1], ordinary[2], f"{loc}/{k}", note))
        for ci, pc in enumerate(module_rows):
            course = pc.get("course") or {}
            name = str(course.get("nameZh") or course.get("name") or "").strip()
            code = str(course.get("code") or "").strip()
            if not name:
                # Keep uncoded/unlabelled source rows traceable in the full index.
                name = code or "原表未列课程名称"
            key = code or f"ROW:{pid}:{mi}:{ci}"
            row_loc = f"{loc}/planCourses/{ci}"
            node = courses.setdefault(key, {"id": key, "names": [], "plan_ids": [], "public_only": True})
            if name not in node["names"]:
                node["names"].append(name)
            if pid not in node["plan_ids"]:
                node["plan_ids"].append(pid)
            if not public:
                node["public_only"] = False
            row = {"plan": pid, "id": key, "code": code, "name": name, "module": mi, "row": ci,
                   "terms": pc.get("terms") or [], "suggest_terms": pc.get("suggestTerms") or [],
                   "credits": course.get("credits"), "compulsory": pc.get("compulsory"),
                   "opening_department": (pc.get("openDepartment") or {}).get("nameZh"),
                   "required_course": pc.get("requiredCourse"), "public_reference": public}
            rows.append(row)
            placements[key].append(row)
            member_courses[mi].add(key)
            if not public:
                by_name[norm(name)].add(key)
                if code:
                    by_name[norm(code)].add(key)
            for obj, prefix in [(pc, row_loc), (course, row_loc + "/course")]:
                for field, value in obj.items():
                    if not isinstance(value, str) or not value.strip():
                        continue
                    if PRE_FIELD.search(field):
                        contextual.append((key, f"{prefix}/{field}", "先修课程：" + plain(value)))
                    elif field in {"remark", "claim"} and KEYWORD.search(value):
                        contextual.append((key, f"{prefix}/{field}", plain(value)))

    with zipfile.ZipFile(doc_path) as archive:
        check(archive.testzip() is None, f"{doc_path}: CRC")
        document = ET.fromstring(archive.read("word/document.xml"))
        for pi, paragraph in enumerate(document.iter(WORD + "p")):
            line = "".join(item.text or "" for item in paragraph.iter(WORD + "t"))
            if KEYWORD.search(line):
                clauses.extend((f"word/document.xml#p{pi}", s.strip()) for s in re.split(r"[。；\n]", line) if KEYWORD.search(s))

    def unique(name):
        candidates = by_name.get(norm(name), set())
        return next(iter(candidates)) if len(candidates) == 1 else None

    edges = {}
    def add(a, b, kind, reason, evidence=None):
        if not a or not b or a == b:
            return
        if kind == "content":
            a, b = sorted((a, b))
        key = (kind, a, b)
        if key not in edges:
            refs = []
            for code in (a, b):
                r = placements[code][0]
                refs.append(f"/courseModules/{r['module']}/planCourses/{r['row']}")
            edges[key] = {"type": kind, "from": a, "to": b, "basis": reason, "rows": refs}
        if evidence:
            ev = edges[key].setdefault("evidence", [])
            if evidence not in ev:
                ev.append(evidence)

    def prepare(a, b, why):
        if not a or not b or a == b:
            return
        add(a, b, "recommended_preparation", why)
        left = [number_terms(r["terms"]) for r in placements[a]]
        right = [number_terms(r["terms"]) for r in placements[b]]
        if all(left + right) and max(max(x) for x in left) < min(min(x) for x in right):
            add(a, b, "term_order", "同方案该课程全部明确数字学期均早于后者。")

    series = collections.defaultdict(lambda: collections.defaultdict(set))
    for key, in_plan in placements.items():
        for item in in_plan:
            if item["public_reference"]:
                continue
            title = item["name"]
            stage = title_series(title)
            if stage:
                family, ordinal = stage
                series[family][ordinal].add(key)
            practice = PRACTICE.fullmatch(norm(title))
            if practice:
                add(unique(practice[1]), key, "content", "题名显示相同主题的课程与实验、实践或实习。")
    for family, stages in series.items():
        levels = sorted(stages)
        for a, b in zip(levels, levels[1:]):
            if b != a + 1 and not (family[2] == "parts" and [a, b] == [1, 3]):
                continue
            if len(stages[a]) == len(stages[b]) == 1:
                prepare(next(iter(stages[a])), next(iter(stages[b])), "同方案的课程题名具有连续分册或序号。")
    for source, target, why in SEQUENCES:
        prepare(unique(source), unique(target), why)
    for a, b, theme in THEMES:
        add(unique(a), unique(b), "content", "共同主题为" + theme + "。")
    rules_file = Path(__file__).with_name("extra-rules.json")
    if rules_file.exists():
        extra = json.loads(rules_file.read_bytes())
        scoped = extra.get("by_department", {}).get((model.get("department") or {}).get("nameZh"), {})
        for rules in (extra, scoped):
            for a, b, why in rules.get("preparation", []):
                prepare(unique(a), unique(b), why)
            for a, b, why in rules.get("content", []):
                add(unique(a), unique(b), "content", why)
    literal_topic_links(placements, unique, add, prepare)
    matched_sequence_notes = []
    for left, right, locator, note in sequences:
        a, b = unique(left), unique(right)
        if a and b and a != b:
            add(a, b, "official_sequence", "原表指定普通路线为大一上学期、下学期依次修读，并另列可选路线。",
                {"at": locator, "text": note})
            matched_sequence_notes.append(norm(note))

    unresolved = set()
    def parse_refs(target, statement, locator):
        match = FORMS.fullmatch(statement)
        if not match:
            return False
        sources = [unique(t) for t in split_sources(match[1])]
        if not sources or not all(sources) or target in sources:
            return False
        for source in sources:
            add(source, target, "official_preparation", "方案原文列明预修课程。", {"at": locator, "text": statement})
        return True

    for key, locator, text in contextual:
        for statement in filter(None, map(str.strip, re.split(r"[。\n]", text))):
            if not parse_refs(key, statement, locator):
                unresolved.add((locator, statement))
    for locator, statement in clauses:
        if "修读顺序" in statement and any(norm(statement) in note for note in matched_sequence_notes):
            continue
        match = re.fullmatch(r"《([^》]+)》(?:的)?((?:先修|预修|前置课程|前序课程|先行课程).+)", statement)
        target = unique(match[1]) if match else None
        if not target or not parse_refs(target, match[2], locator):
            unresolved.add((locator, statement))
    # Disciplinary module membership supplies an explicit topic even where individual
    # syllabuses are unavailable. Store it as a hyperedge, without inventing all-to-all pairs.
    topics = []
    generic = re.compile(r"^(?:[A-Z]组|[一二三四五六七八九十\d]+选[一二三四五六七八九十\d]+|[A-Z]?类|其他|普通班|荣誉课程|专业培养课程|培养方案|必修课程?|选修课程?|限定必修课程?|专业选修课程?|专业必修课程?|通识教育.*|大类基础课程?|专业核心教育课程?|学科基础课程?|专业进阶.*|任意选修.*|融合创新能力|课程组.*)$")
    for mi, members in sorted(member_courses.items()):
        title = module_title(modules[mi])
        if len(members) >= 2 and not generic.fullmatch(title) and not all(r["public_reference"] for key in members for r in placements[key] if r["module"] == mi):
            topics.append({"module": mi, "name": title, "courses": sorted(members), "type": "shared_named_module"})
    return {"id": pid, "title": meta["title"], "department": (model.get("department") or {}).get("nameZh"),
            "url": meta.get("detail_url", ""), "major": (model.get("major") or {}).get("nameZh"),
            "student_type": (model.get("stdType") or {}).get("nameZh"), "course_count": len(placements),
            "rows": sum(map(len, placements.values())), "modules": len(modules),
            "plan_json_sha256": digest(raw_bytes), "word_sha256": digest(doc_path.read_bytes()),
            "edges": list(edges.values()), "module_groups": topics,
            "unresolved": [{"at": loc, "text": s} for loc, s in sorted(unresolved)]}


def plan_page(plan, courses, plan_modules, plan_rows):
    pid = plan["id"]
    names = {r["id"]: r["name"] for r in plan_rows}
    lines = [
        "# " + md(plan["title"]), "",
        f'{md(plan.get("department") or "")} · {md(plan.get("major") or "")} · 方案 {pid} · {plan["course_count"]} 个不同课程或科研条目。', "",
        f'[官方 Word](../originals/plan-{pid}.docx) · [教务详情]({plan["url"]}) · [方案快照](../raw/plan-{pid}.json.gz) · [年级目录](../README.md)', "",
        "## 课程关系图", "",
    ]
    edges = plan["edges"]
    by_type = {kind: [e for e in edges if e["type"] == kind] for kind in LABELS}
    shown = []
    shown_pairs = set()
    own = {r["id"] for r in plan_rows if r.get("opening_department") == plan.get("department")}
    core = {r["id"] for r in plan_rows if "专业核心" in plan_modules[r["module"]]["path"]}
    def relevance(e):
        return -sum(2 * (c in own) + (c in core) for c in [e["from"], e["to"]])
    for kind in ["official_preparation", "official_sequence", "term_order", "content", "recommended_preparation"]:
        count = 0
        for e in sorted(by_type[kind], key=relevance):
            pair = (e["from"], e["to"])
            if pair in shown_pairs:
                continue
            shown.append(e)
            shown_pairs.add(pair)
            count += 1
            if count >= 5:
                break
    mermaid = ["```mermaid", "flowchart LR"]
    labels = {}
    def node(key, label):
        if key not in labels:
            nid = f"N{len(labels) + 1}"
            labels[key] = nid
            mermaid.append(f'  {nid}["{mermaid_label(label)}"]')
        return labels[key]
    for e in shown:
        a, b = node(e["from"], names[e["from"]]), node(e["to"], names[e["to"]])
        arrow = "---" if e["type"] == "content" else "-->"
        mermaid.append(f'  {a} {arrow}|{LABELS[e["type"]]}| {b}')
    if not shown:
        groups = collections.defaultdict(list)
        for r in plan_rows:
            if not r["public_reference"] and r["id"] not in groups[r["module"]]:
                groups[r["module"]].append(r["id"])
        if not groups:
            for r in plan_rows:
                if r["id"] not in groups[r["module"]]:
                    groups[r["module"]].append(r["id"])
        for mi, members in list(groups.items())[:4]:
            a = node(("module", mi), plan_modules[mi]["path"].split(" / ")[-1])
            for key in members[:3]:
                b = node(key, names[key])
                mermaid.append(f'  {a} ---|模块收录| {b}')
    if labels:
        lines.extend(mermaid + ["```", ""])
    else:
        lines.extend(["公开方案未列出可定位的课程行。课程设置请查阅上方原件。", ""])
    lines += ["图中展示部分关系。下表保留全部已建立的课程对，来源位置使用本方案 JSON Pointer。", "",
              "## 先修与内容联系", ""]
    if edges:
        lines += ["| 类型 | 起点 | 终点 | 依据 | 原表定位 |", "| --- | --- | --- | --- | --- |"]
        for e in sorted(edges, key=lambda v: (list(LABELS).index(v["type"]), v["from"], v["to"])):
            evidence = " ".join(md(ev["text"]) for ev in e.get("evidence", []))
            locs = "、".join("`" + p + "`" for p in e["rows"])
            locs += "".join("、`" + ev["at"] + "`" for ev in e.get("evidence", []))
            lines.append(f'| {LABELS[e["type"]]} | {md(names[e["from"]])} ({md(e["from"])}) | {md(names[e["to"]])} ({md(e["to"])}) | {md(e["basis"])} {evidence} | {locs} |')
    else:
        lines.append("现有原文和课程题名不足以建立可定位的课程对。")
    if not by_type["official_preparation"]:
        lines += ["", "本次未从可定位的明确表述中确认课程对课程预修。学期安排、系列分册与编辑建议均保留各自的依据。"]
    if plan["unresolved"]:
        lines += ["", "### 需人工核对的原文", ""]
        for cue in plan["unresolved"]:
            lines.append(f'- `{cue["at"]}`　{md(cue["text"][:700])}')
    if plan["module_groups"]:
        lines += ["", "## 按原方案模块阅读", "", "同一模块展示原表中的课程归属。模块内课程之间的先后仍须逐项查阅。", ""]
        for g in plan["module_groups"]:
            listed = g["courses"][:18]
            more = "等" + str(len(g["courses"])) + "项" if len(listed) < len(g["courses"]) else ""
            lines.append(f'- **{md(g["name"])}**　' + "、".join(md(names[k]) for k in listed) + more + f'（原表模块 {g["module"]}）')
    lines += ["", "## 课程表", "", "同一课程在不同模块分别出现时，按原表逐行列出。季节字段保留原值。", "",
              "| 课程 | 代码 | 学分 | 学期 | 模块 |", "| --- | --- | ---: | --- | --- |"]
    for r in plan_rows:
        terms = "、".join(str(v).replace("TERM_", "第") + ("学期" if str(v).startswith("TERM_") else "") for v in r["terms"])
        lines.append(f'| {md(r["name"])} | {md(r["code"])} | {md(r["credits"]) if r["credits"] is not None else ""} | {md(terms)} | {md(plan_modules[r["module"]]["path"])} |')
    return "\n".join(lines).rstrip() + "\n"


def build_year(year_dir):
    metas = json.loads((year_dir / "programmes.json").read_text("utf-8-sig"))
    check(isinstance(metas, list), f"{year_dir}: programmes.json is not an array")
    ids = [str(m["id"]) for m in metas]
    check(len(ids) == len(set(ids)), f"{year_dir}: duplicate programme id")
    courses, rows, modules, plans = {}, [], [], []
    counts = collections.Counter()
    for meta in sorted(metas, key=lambda m: str(m["id"])):
        row_start, module_start = len(rows), len(modules)
        p = build_plan(year_dir, meta, courses, rows, modules)
        plan_rows, plan_modules = rows[row_start:], modules[module_start:]
        check(p["rows"] == len(plan_rows), f'{p["id"]}: row count')
        check(all(e["from"] in courses and e["to"] in courses for e in p["edges"]), f'{p["id"]}: missing graph endpoint')
        write(year_dir / "plans" / f'{p["id"]}.md', plan_page(p, courses, plan_modules, plan_rows))
        counts.update(e["type"] for e in p["edges"])
        plans.append(p)
    departments = sorted({p["department"] for p in plans if p["department"]})
    dept = "、".join(departments) or year_dir.parent.name
    names = sorted({name for n in courses.values() for name in n["names"] if name != "原表未列课程名称"})
    write(year_dir / "课程名单.txt", "\n".join(names) + ("\n" if names else ""))
    index = {"schema": "fudan-school-courses/1", "cohort": int(year_dir.name), "departments": departments,
             "locator": "/courseModules/{module}/planCourses/{row}", "courses": list(courses.values()), "rows": rows, "modules": modules}
    write(year_dir / "courses.json.gz", gzip.compress(encode(index), compresslevel=6, mtime=0))
    graph = {"schema": "fudan-school-graph/1", "cohort": int(year_dir.name), "departments": departments, "relation_types": LABELS,
             "course_nodes": list(courses.values()), "plans": plans,
             "summary": {"plans": len(plans), "courses": len(courses), "course_rows": len(rows), "relations_by_type": dict(counts),
                         "uncoded_rows": sum(not r["code"] for r in rows),
                         "module_groups": sum(len(p["module_groups"]) for p in plans), "unresolved_mentions": sum(len(p["unresolved"]) for p in plans)}}
    write(year_dir / "graph.json", encode(graph))
    lines = [f"# {dept} {year_dir.name} 级培养方案与课程关系", "",
             f"共 {len(plans)} 份官方培养方案，原表 {len(rows)} 行，共 {len(courses)} 个课程代码或无代码独立条目。每份方案的图谱与课程表均可直接在 GitHub 阅读。", "",
             "[课程名单](课程名单.txt) · [完整课程索引](courses.json.gz) · [课程图谱数据](graph.json) · [方案目录](programmes.json)", "",
             "| 培养方案与关系图 | Word 原件 | 原始数据 | 方案内条目 | 已明确预修 |", "| --- | --- | --- | ---: | ---: |"]
    for p in plans:
        pid = p["id"]
        count = sum(e["type"] == "official_preparation" for e in p["edges"])
        lines.append(f'| [{md(p["title"])}](plans/{pid}.md) | [下载](originals/plan-{pid}.docx) | [JSON](raw/plan-{pid}.json.gz) | {p["course_count"]} | {count} |')
    lines += ["", "方案列明预修要求时，可从关系表追溯原句和位置。数字学期只表达同一方案的安排。连续分册和学科基础建议由编辑规则生成。课程内容联系依据课程题名或原方案的模块归属，具体修读资格以教务和适用大纲为准。", "",
              "各版本分别匹配课号与名称。原表列出的通识、选修候选与科研环节也收录在课程索引中，统计覆盖全部方案条目。空引用模块保留在模块索引中。仅以图片呈现的路线可在对应 Word 中查阅。", "",
              "原始 JSON 采用 gzip 压缩。完整索引中的 plan、module、row 可定位到原始课程行。原件和压缩快照的 SHA-256 收录于 graph.json 的方案记录。"]
    write(year_dir / "README.md", "\n".join(lines) + "\n")
    return graph["summary"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("department", type=Path)
    parser.add_argument("--year", type=int, choices=range(2023, 2026))
    args = parser.parse_args()
    years = [args.year] if args.year else [y for y in range(2023, 2026) if (args.department / str(y) / "programmes.json").exists()]
    check(bool(years), f"No 2023–2025 cohort manifest found in {args.department}")
    for year in years:
        print(json.dumps({"department": args.department.name, "year": year, **build_year(args.department / str(year))}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
