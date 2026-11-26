"""Build navigable cohort graphs from verified registrar data and sourced rules.

Usage: python build_cohort_graph.py DIRECTORY_WITH_YEAR_SUBDIRECTORIES
Each year directory has plans.json, courses.json, and relations.json. The
editorial reference contains only course names and subject/preparation edges.
"""

from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import re
import sys
import unicodedata

YEARS = (2023, 2024, 2025)
KINDS = {
    'formal_prerequisite': ('正式先修', True),
    'prerequisite_topic': ('官方先修领域', True),
    'official_sequence': ('官方修读顺序', True),
    'official_credit_waiver': ('官方替代或免修', True),
    'official_equivalence': ('官方课号或学分认定', False),
    'recommended_preparation': ('建议先学', True),
    'content_related': ('内容联系', False),
    'module_course': ('培养方案课程', False),
    'plan_module': ('培养方案模块', False),
}


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def normalized(name):
    # Preserve H and numeric suffixes. Only normalize layout and punctuation.
    return re.sub(r'[\s《》〈〉“”‘’\(\)\[\]：:·、,，\-—]', '', unicodedata.normalize('NFKC', name)).casefold()


def short_section(course):
    return str(course.get('module') or '').strip() or '原表未标模块'


def plan_title(plan):
    return str(plan.get('name') or plan.get('title') or plan['id'])


def make_graph(year, directory, reference):
    plans = load(directory / 'plans.json')
    plan_map = {str(p['id']): p for p in plans}
    assert len(plans) == len(plan_map), f'{year}: duplicate plans'
    rows = load(directory / 'courses.json')
    official = load(directory / 'relations.json')
    nodes = {}
    edges = []
    course_memberships = defaultdict(set)
    course_names = defaultdict(set)
    aliases = defaultdict(set)
    grouped = defaultdict(list)
    for i, row in enumerate(rows, 1):
        code = str(row.get('code') or '').strip()
        plan_id = str(row['plan_id'])
        name = str(row.get('name') or '').strip()
        if not (code and name and plan_id in plan_map):
            raise ValueError(f'{year} invalid course row {i}')
        group = short_section(row)
        grouped[plan_id, group, row.get('module_id'), code].append(i)
        course_memberships[code].add(plan_id)
        course_names[code].add(name)
        aliases[normalized(name)].add(code)

    def add_edge(source, target, kind, evidence, **attrs):
        assert source in nodes and target in nodes and source != target, (year, source, target)
        label, directed = KINDS[kind]
        if not directed and kind in {'content_related', 'official_equivalence'}:
            source, target = sorted((source, target))
        assert evidence, (year, source, target)
        edges.append({'source': source, 'target': target, 'kind': kind, 'directed': directed,
                      'is_formal_prerequisite': kind == 'formal_prerequisite',
                      'evidence': evidence, **attrs})

    for code, names in sorted(course_names.items()):
        nodes[code] = {'id': code, 'type': 'course', 'code': code,
                       'name': sorted(names, key=lambda n: (len(n), n))[0],
                       'names': sorted(names), 'plan_ids': sorted(course_memberships[code])}
    for pid, plan in plan_map.items():
        node_id = f'plan:{pid}'
        nodes[node_id] = {'id': node_id, 'type': 'plan', 'name': plan_title(plan), 'plan_ids': [pid]}
    modules = defaultdict(dict)
    for (pid, module, module_id, code), positions in grouped.items():
        plan_node = f'plan:{pid}'
        module_key = (module_id, module)
        if module_key not in modules[pid]:
            m = f'module:{pid}:{len(modules[pid]) + 1}'
            modules[pid][module_key] = m
            nodes[m] = {'id': m, 'type': 'module', 'name': module, 'plan_ids': [pid], 'official_module_id': module_id}
            add_edge(plan_node, m, 'plan_module', [{'path': 'courses.json', 'rows': positions}],
                     plan_ids=[pid], authority='official', rationale='该模块列在该培养方案课程表中。')
        m = modules[pid][module_key]
        add_edge(m, code, 'module_course', [{'path': 'courses.json', 'rows': positions}],
                 plan_ids=[pid], authority='official', rationale='该课列在该方案的此模块。')

    official_aliases = {
        'official_order': 'official_sequence', 'sequence': 'official_sequence',
        'waiver': 'official_credit_waiver', 'credit_waiver': 'official_credit_waiver',
        'credit_substitution': 'official_credit_waiver', 'substitution': 'official_credit_waiver',
        'prerequisite': 'formal_prerequisite',
        'official_prerequisite': 'formal_prerequisite', 'recommendation': 'recommended_preparation',
    }
    pending = []
    explicit_pairs = set()
    for record in official:
        kind = official_aliases.get(record['kind'], record['kind'])
        if kind == 'formal_prerequisite' and record.get('exact_course_required') is False:
            kind = 'prerequisite_topic'
        if kind not in {'formal_prerequisite', 'prerequisite_topic', 'official_sequence', 'official_credit_waiver', 'official_equivalence', 'recommended_preparation'}:
            raise ValueError(f'{year}: unknown official relation {kind!r}')
        source = str(record['source']).strip()
        target = str(record['target']).strip()
        if source not in nodes or target not in nodes:
            pending.append({**record, 'status': '课程端点未在该年级教务课程表唯一定位'})
            continue
        evidence = record['evidence']
        if isinstance(evidence, dict):
            evidence = [evidence]
        evidence += [e for e in record.get('additional_evidence', []) if e.get('url') and e.get('locator')]
        if not all(e.get('url') and e.get('locator') for e in evidence):
            raise ValueError(f'{year}: official rule without a URL and locator')
        scope = record.get('scope')
        plan_ids = sorted(str(x) for x in record.get('plan_ids', scope if isinstance(scope,list) else []))
        assert set(plan_ids) <= set(plan_map)
        attrs = {k: v for k, v in record.items() if k not in {'source','target','kind','evidence','additional_evidence','authority','plan_ids','is_formal_prerequisite','directed'}}
        if isinstance(scope,list):
            attrs['scope'] = '涉及方案 ' + '、'.join(str(x) for x in scope)
        if record.get('scope_note'):
            attrs['scope'] += '。' + record['scope_note']
        assert attrs.get('scope') and attrs.get('rationale'), (year, record)
        add_edge(source, target, kind, evidence, plan_ids=plan_ids, authority='official', **attrs)
        if kind in {'formal_prerequisite', 'official_sequence', 'recommended_preparation'}:
            explicit_pairs.add((source,target))

    def match_reference(code):
        name = reference['names'][code]
        current = aliases.get(normalized(name), set())
        if code in current:
            return code
        if len(current) == 1:
            return next(iter(current))
        return None

    editorial = set()
    for record in reference['edges']:
        a, b = match_reference(record['source']), match_reference(record['target'])
        if not a or not b or a == b:
            continue
        plans_in_common = sorted(course_memberships[a] & course_memberships[b])
        if not plans_in_common:
            continue
        kind = record['kind']
        if kind == 'recommended_preparation' and (a,b) in explicit_pairs:
            continue
        endpoints = (a, b) if KINDS[kind][1] else tuple(sorted((a, b)))
        key = (*endpoints, kind)
        if key in editorial:
            continue
        editorial.add(key)
        add_edge(a, b, kind, [{'path': '../../课程关系图谱/graph.json', 'id': record['id']},
                             {'path': 'courses.json', 'codes': list(endpoints)}],
                 plan_ids=plans_in_common, authority='editorial_inference', rationale=record['rationale'],
                 scope=f'{year}级，按两端正式课名和对应年级课程表匹配')

    for i, edge in enumerate(edges, 1):
        edge['id'] = f'{year}-E{i:05d}'
    counts = dict(Counter(e['kind'] for e in edges))
    graph = {'schema_version': '1.0', 'year': year,
             'course_scope': '当年级教务培养方案所列课程及相应模块，包括跨院系修读课程。',
             'plans': [{**p, 'id': str(p['id'])} for p in plans],
             'kinds': {k: {'label': label, 'directed': directed} for k, (label, directed) in KINDS.items()},
             'nodes': list(nodes.values()), 'edges': edges,
             'statistics': {'plans': len(plans), 'courses': len(course_names), 'course_rows': len(rows),
                            'modules': sum(len(groups) for groups in modules.values()), 'edge_counts': counts},
             'pending_official_rules': pending,
             'source_hashes': {name: hashlib.sha256((directory/name).read_bytes()).hexdigest()
                               for name in ('plans.json','courses.json','relations.json')}}
    save(directory / 'graph.json', graph)
    return graph


def main(root):
    reference = load(root / 'editorial-reference.json')
    graphs = [make_graph(year, root / str(year), reference) for year in YEARS]
    template = (root / 'viewer.template.html').read_text(encoding='utf-8')
    compact = [{**{k: g[k] for k in ('year','kinds','nodes','edges','statistics')},
                'plans': [{'id': p['id'], 'name':p['name']} for p in g['plans']]} for g in graphs]
    serialized = json.dumps(compact, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    (root / 'index.html').write_bytes(template.replace('__GRAPHS__', serialized).encode('utf-8'))
    for graph in graphs:
        print(graph['year'], json.dumps(graph['statistics'], ensure_ascii=False))


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent)
