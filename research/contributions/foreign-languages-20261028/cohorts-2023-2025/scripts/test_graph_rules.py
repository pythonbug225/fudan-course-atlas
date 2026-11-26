"""Meaningful graph-rule regression tests; no network or third-party libraries.

Run: python scripts/test_graph_rules.py
Uses minimal official-shaped fixtures in a temporary directory, never real outputs.
"""
import contextlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('graph_builder', Path(__file__).with_name('build_graphs.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def course(code, name, identity=1):
    return {'id': identity, 'course': {'id': identity, 'code': code, 'nameZh': name}, 'openDepartment': {'nameZh': '外国语言文学学院'}}


class GraphRules(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='foreign-graph-rules-')
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        self.previous_root = builder.ROOT
        builder.ROOT = self.root
        self.official = self.root / 'cohorts/2023/official'
        (self.official / 'raw').mkdir(parents=True)
        (self.official / 'word-originals').mkdir()

    def tearDown(self):
        builder.ROOT = self.previous_root
        self.temp.cleanup()

    def graph(self, plans):
        manifest = []
        for pid, modules in plans:
            pid = str(pid)
            manifest.append({'plan_id': pid, 'cohort': 2023, 'title': f'Test {pid}'})
            raw = {'model': {'id': pid, 'grade': '2023', 'nameZh': f'Test {pid}'}, 'courseModules': modules}
            (self.official / 'raw' / f'plan-{pid}.json.gz').write_bytes(gzip.compress(json.dumps(raw).encode()))
            with zipfile.ZipFile(self.official / 'word-originals' / f'plan-{pid}.docx', 'w') as z:
                z.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>')
        (self.official / 'programmes.json').write_text(json.dumps(manifest), 'utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            builder.build(2023)
        return json.loads((self.root / 'cohorts/2023/course-graph/graph.json').read_text('utf-8'))

    def test_upper_middle_lower_never_skips_middle(self):
        g = self.graph([(1, [{'id': 10, 'nameZh': '模块', 'planCourses': [course('FORE1', '第二外语（日语）（上）', 1), course('FORE2', '第二外语（日语）（中）', 2), course('FORE3', '第二外语（日语）（下）', 3)]}])])
        pairs = {(e['source'], e['target']) for e in g['edges'] if e['type'] == 'suggested_sequence'}
        self.assertEqual(pairs, {('FORE1', 'FORE2'), ('FORE2', 'FORE3')})

    def test_upper_lower_and_numbered_sequences(self):
        self.assertTrue(builder.consecutive((0, 1), (0, 3), [(0, 1), (0, 3)]))
        self.assertFalse(builder.consecutive((0, 1), (0, 3), [(0, 1), (0, 2), (0, 3)]))
        self.assertEqual(builder.sequence('笔译理论（一）'), ('笔译理论', (1, 0)))
        self.assertEqual(builder.sequence('第二外语（日语）（上）'), ('第二外语(日语)', (0, 1)))
        self.assertEqual(builder.sequence('综合日语Ⅱ（下）'), ('综合日语', (2, 3)))
        self.assertTrue(builder.consecutive((1, 3), (2, 1), [(1, 3), (2, 1)]))
        self.assertFalse(builder.consecutive((1, 0), (3, 0), [(1, 0), (3, 0)]))

    def test_repeated_virtual_module_ids_stay_distinct(self):
        g = self.graph([(1, [{'id': 2, 'nameZh': '专业进阶路径', 'planCourses': [course('FORE1', '英语精读')]}, {'id': 2, 'nameZh': '融合创新能力', 'planCourses': [course('FORE2', '英语写作', 2)]}])])
        modules = [n for n in g['nodes'] if n['kind'] == 'module']
        self.assertEqual(len(modules), 2)
        self.assertEqual({n['module_source_id'] for n in modules}, {'2'})
        self.assertEqual(len({n['id'] for n in modules}), 2)
        memberships = [e for e in g['edges'] if e['type'] == 'program_module']
        self.assertEqual(len({e['target'] for e in memberships}), 2)

    def test_no_sequence_between_different_programs(self):
        g = self.graph([(1, [{'id': 10, 'nameZh': '模块', 'planCourses': [course('FORE1', '英语写作（上）')]}]), (2, [{'id': 10, 'nameZh': '模块', 'planCourses': [course('FORE2', '英语写作（下）', 2)]}])])
        self.assertFalse(any(e['type'] == 'suggested_sequence' for e in g['edges']))

    def test_evidence_pointers_resolve_and_duplicate_arrays_deduplicate(self):
        first, second = course('FORE1', '英语写作（上）', 1), course('FORE2', '英语写作（下）', 2)
        g = self.graph([(1, [{'id': 10, 'nameZh': '模块', 'planCourses': [first, second], 'realPlanCourses': [first, second]}])])
        self.assertEqual(g['statistics']['course_membership_rows'], 2)
        for edge in g['edges']:
            for evidence in edge['evidence']:
                source = self.root / 'cohorts/2023' / evidence['source_path']
                value = json.loads(gzip.decompress(source.read_bytes()))
                for part in evidence['json_pointer'].strip('/').split('/'):
                    key = part.replace('~1', '/').replace('~0', '~')
                    value = value[int(key)] if isinstance(value, list) else value[key]
                self.assertIn(value['course']['code'], {edge['source'], edge['target']})


if __name__ == '__main__':
    unittest.main()
