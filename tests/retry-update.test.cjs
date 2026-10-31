const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),vm=require('node:vm');
const root=path.resolve(__dirname,'../public'),read=n=>require('../scripts/read-catalog.cjs')(path.join(root,'data',n+'.json'));
const catalog=read('catalog'),update=read('retry-update'),supp=read('review-supplement'),syn=read('course-summaries');
assert.equal(update.new_syllabus_bodies,0);assert.equal(update.authenticated_controls,2);
assert.equal(update.availability.length,170);assert.equal(update.availability.filter(x=>x.previous_state==='blank').length,43);
assert.equal(catalog.scope.length,update.before.courses);assert.equal(catalog.syllabi.length,update.before.syllabi);
assert.equal(supp.records.length,update.before.supplement_records+1);
const norm=s=>s.normalize('NFKC').replace(/\s+/g,'').toUpperCase();
for(const row of update.availability){
 const g=catalog.scope.find(g=>g.id===row.course_id),o=g.offerings.find(o=>o.official_lesson_id===row.lesson_id);
 assert(o);assert.equal(o.term,row.term);assert.equal(norm(o.code),norm(row.section_code));assert.deepEqual([...o.teachers].sort(),[...row.teachers].sort());
 assert.equal(o.syllabus_availability.status,'not_approved');assert(!o.syllabus);
 assert.equal(o.syllabus_availability.message,'该教学任务暂无审核通过的学期课程教学大纲');
}
const app=fs.readFileSync(path.join(root,'assets/app.js'),'utf8');const renderLine=app.split('\n').find(l=>l.startsWith('function parallelSyllabiHTML('));
const box={E:x=>String(x)};vm.runInNewContext(renderLine+';this.render=parallelSyllabiHTML;',box);
assert.equal(update.parallel_references.length,9);
for(const p of update.parallel_references){
 const g=catalog.scope.find(g=>g.id===p.course_id),target=g.offerings.find(o=>o.official_lesson_id===p.target_lesson_id);assert(target&&!target.syllabus);
 const html=box.render(target);assert(html.includes('平行班参照'));
 for(const r of target.syllabus_references){
  const s=catalog.syllabi.find(s=>String(s.lesson_id)===String(r.lesson_id));assert(s&&!s.summary_only);
  assert.equal(norm(s.course_code),norm(g.code));assert.equal(s.term,target.term);assert.deepEqual([...s.teachers].sort(),[...target.teachers].sort());
  const source=g.offerings.find(o=>o.term===r.term&&norm(o.code)===norm(r.section_code));assert(source&&source.class_type===target.class_type);
  assert(html.includes(`data-inline-syllabus="${r.lesson_id}"`));assert(html.includes(r.section_code));
 }
}
for(const cid of update.historical_experience_courses){
 const g=catalog.scope.find(g=>g.id===cid),s=syn.records.find(s=>s.id===cid);assert(g.student_evaluation.has_reviews&&s.historical_student_experience);
 const rows=supp.records.filter(r=>r.course_ids.includes(cid)&&r.source_story_family==='FUDAN-AI-E-2024-HISTORICAL');assert.equal(rows.length,1);
 assert(rows[0].term.includes('推定'));assert(!rows[0].source_url);assert(rows[0].student_experience_verified);
 assert(syn.sources[s.historical_student_experience.source_ref]);
}
assert(!/wxid_|@chatroom|xsec_token|SAMLResponse|loginToken|D:\\\\danxi/.test(JSON.stringify(update)));
console.log('Retry availability, exact class references, historical source deduplication and current syllabus preservation verified.');
