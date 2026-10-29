"""Record source counts without treating duplicate course mappings as people."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
load = lambda n: json.loads((ROOT/n).read_text(encoding='utf8'))
data = load('dataset.json'); verification = load('verification.json')
records = load('review_sources.json')['records']
danke = {r['id']:r for r in records if r['id'].startswith('danxi_review_')}
forum = {}
for r in records:
    ids = r.get('source_ids') or {}
    if ids.get('floor_id'): forum[(str(ids['hole_id']),str(ids['floor_id']))] = r
audit = load('forum_reading_audit.json')
stats = {
    'scope': '大数据学院2025秋与2026春开课，评价允许相关历史或后续学期并标明',
    'course_count':len(data['courses']), 'teaching_section_count':146,
    'professional_program_count':7, 'public_program_count':1,
    'syllabus_sections_with_body':83, 'courses_with_syllabus':78, 'syllabus_http_500_sections':63,
    'exact_enrollment_capacity_matches':146,
    'danke_unique_review_ids':len(danke), 'danke_full_original_texts':sum(bool(r.get('full_text')) for r in danke.values()),
    'forum_selected_unique_floors':len(forum), 'forum_selected_unique_holes':len({k[0] for k in forum}),
    'student_source_course_count':verification['courses_with_student_evaluation'],
    'current_instructor_source_course_count':verification['courses_with_current_teacher_evaluation'],
    'courses_without_collected_student_evaluation':84-verification['courses_with_student_evaluation'],
    'original_review_text_characters_including_spaces_punctuation':sum(len(r.get('full_text','')) for r in danke.values()),
    'selected_discussion_characters_including_spaces_punctuation':sum(len(r.get('full_text','')) for r in forum.values()),
    'local_cache_files_scanned':13493, 'candidate_unique_floors_screened':audit['decision_count'],
    'candidate_floors_manually_read_unique':audit['unique_manually_read_floors'],
    'candidate_floors_not_individually_manually_read':audit['not_individually_manually_read_floors'],
    'group_chat_sources':6, 'group_chat_messages':135786, 'group_chat_context_packets_reviewed':115,
    'public_full_course_names_submitted':84, 'public_current_offering_reviews_adopted':0,
    'notes':['同一楼层涉及多门课会映射到多个课程页，不能把映射条数当独立原评数或学生人数。','公开平台只完成索引检索与可读正文筛选，不代表站内穷尽。','未缓存的同洞上下文或仍多义内容保持未归属；未收录评价不代表课程不存在评价。','课程资料目录中的上游文件链接需联网；包内大纲、方案、体系图和所选文字原文可离线查看。']
}
(ROOT/'coverage.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf8')
readme=ROOT/'README.md'; text=readme.read_text(encoding='utf8'); marker='\n<!-- GENERATED_COVERAGE -->'
text=text.split(marker)[0]
text+=marker+'\n\n## 本次收录计数\n\n'
text+=f"{len(danke)} 条去重蛋壳课评，其中 {stats['danke_full_original_texts']} 条保留完整文字原评、1条仅摘要；树洞采用 {len(forum)} 个所选楼层，来自 {stats['forum_selected_unique_holes']} 个洞。学生评价或实质讨论覆盖 {stats['student_source_course_count']} 门，其中 {stats['current_instructor_source_course_count']} 门含可对应当前任课教师的来源；其余课程保留未收录标记。\n\n"
text+=f"1,052个去重楼层均已形成采用、排除或未归属判定，其中{audit['unique_manually_read_floors']}个逐楼AI核读，其余为规则筛查、重复来源或复用判定；机器初筛与AI复核分层指标不相加。私人群聊原文没有进入公开包。\n\n"
text+='上游教材、试卷目录保留固定版本链接，点击这些外部资料仍需联网；大纲、方案、体系图及已收录原文在包内离线可读。详细计数见 `coverage.json`。\n'
readme.write_text(text,encoding='utf8')
print(json.dumps(stats,ensure_ascii=False))
