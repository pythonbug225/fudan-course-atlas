"""Semantic integrity and provenance checks for the Law course graph."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import unittest

HERE=Path(__file__).resolve().parent
BATCH=HERE.parent


def load(path):return json.loads(path.read_text(encoding='utf8'))


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph=load(HERE/'graph.json');cls.nodes={n['id']:n for n in cls.graph['nodes']}

    def test_complete_official_identity_and_levels(self):
        sections=load(BATCH/'official/sections.json')
        self.assertEqual(set(self.nodes),{s['course_code'] for s in sections})
        self.assertEqual(len(self.nodes),260)
        self.assertEqual(len({n['name'] for n in self.nodes.values()}),244)
        for code,node in self.nodes.items():
            actual=[s for s in sections if s['course_code']==code]
            self.assertEqual(set(node['levels']),{s['course_level'] for s in actual})
            self.assertEqual(set(node['teachers']),{t for s in actual for t in s['teachers']})
            self.assertEqual(set(node['names']),{s['course_name'] for s in actual})

    def test_directions_no_cycles_no_enrollment_claims_and_honors_separation(self):
        adjacency=collections.defaultdict(list);seen=set();ids=set()
        for edge in self.graph['edges']:
            self.assertIn(edge['source'],self.nodes);self.assertIn(edge['target'],self.nodes)
            self.assertNotEqual(edge['source'],edge['target'])
            key=(edge['source'],edge['target'],edge['type']);self.assertNotIn(key,seen);seen.add(key)
            self.assertNotIn(edge['id'],ids);ids.add(edge['id'])
            self.assertFalse(edge['is_enrollment_requirement'])
            self.assertEqual(edge['review_status'],'needs_syllabus_or_teacher_review')
            self.assertEqual(edge['directed'],edge['type']=='recommended_prerequisite')
            if edge['directed']:adjacency[edge['source']].append(edge['target'])
        done=set();active=set()
        def visit(code):
            self.assertNotIn(code,active,'cycle in suggested prerequisites')
            if code in done:return
            active.add(code)
            for child in adjacency[code]:visit(child)
            active.remove(code);done.add(code)
        for code in self.nodes:visit(code)
        for code,n in self.nodes.items():
            if n['honors']:
                self.assertTrue(any(e['type']=='content_relation' and {e['source'],e['target']}=={code,code[:-1]} for e in self.graph['edges']))
                self.assertFalse(any(e['directed'] and code in [e['source'],e['target']] for e in self.graph['edges']))

    def test_plan_evidence_pointers_and_order_are_real(self):
        cache={};source_ids={s['id'] for s in self.graph['sources']}
        for edge in self.graph['edges']:
            self.assertTrue(set(edge['source_refs'])<=source_ids)
            for support in edge['plan_order_support']:
                pid=support['program_id']
                if pid not in cache:cache[pid]=json.loads(gzip.decompress((BATCH/'raw/official/programs'/f'{pid}.json.gz').read_bytes()))
                def pointer(where):
                    node=cache[pid]
                    for key in where.strip('/').split('/'):node=node[int(key)] if isinstance(node,list) else node[key]
                    return node
                left,right=pointer(support['source_pointer']),pointer(support['target_pointer'])
                self.assertEqual(left['course']['code'],edge['source'])
                self.assertEqual(right['course']['code'],edge['target'])
                self.assertLess(max(support['source_terms']),min(support['target_terms']))
                self.assertEqual(support['source_terms'],sorted(int(t[5:]) for t in left['terms'] if t.startswith('TERM_')))
                self.assertEqual(support['target_terms'],sorted(int(t[5:]) for t in right['terms'] if t.startswith('TERM_')))

    def test_audit_source_hashes_and_missing_data(self):
        audit=load(HERE/'source-audit.json')
        self.assertEqual(len(audit['programs']),8)
        self.assertEqual(audit['official_prerequisites_confirmed'],0)
        for plan in audit['programs']:
            self.assertFalse(plan['textual_keyword_hits'])
            self.assertTrue(all(not f['value'] for f in plan['fields']))
        for record in audit['input_files']:
            self.assertEqual(hashlib.sha256((BATCH/record['path']).read_bytes()).hexdigest(),record['sha256'])
        connected={x for e in self.graph['edges'] for x in [e['source'],e['target']]}
        self.assertEqual(set(self.graph['stats']['unmapped_nodes']),set(self.nodes)-connected)

    def test_serializations_and_editorial_rule_pointers(self):
        rules=load(HERE/'rules.json')
        for edge in self.graph['edges']:
            if edge['rule_pointer'].startswith('/'):
                value=rules
                for part in edge['rule_pointer'].strip('/').split('/'):value=value[int(part)] if isinstance(value,list) else value[part]
                self.assertTrue(value)
        with (HERE/'relations.csv').open(encoding='utf8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual({r['id'] for r in rows},{e['id'] for e in self.graph['edges']})
        for row,edge in zip(rows,self.graph['edges']):
            self.assertEqual((row['source'],row['target'],row['reason']),(edge['source'],edge['target'],edge['reason']))
        page=(HERE/'index.html').read_text('utf8')
        embedded=re.search(r'<script id="graph-data" type="application/json">(.*?)</script>',page,re.S).group(1)
        self.assertEqual(json.loads(embedded),self.graph)
        self.assertNotIn('/* GRAPH_CORE */',page)
        self.assertNotIn('src="https://',page)
        for source in self.graph['sources']:self.assertTrue((HERE/source['path']).is_file())


if __name__=='__main__':unittest.main()
