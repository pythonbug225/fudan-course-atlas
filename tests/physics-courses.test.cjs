const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const p=path.resolve(__dirname,'../public');
const read=n=>JSON.parse(fs.readFileSync(path.join(p,'data',n),'utf8'));
const cat=read('catalog.json'),syn=read('course-summaries.json'),en=read('enrollment.json');
const groups=new Map(cat.scope.map(g=>[g.code,g])), summaries=new Map(syn.records.map(r=>[r.id,r]));
assert.equal(cat.stats.physics_course_groups,95);assert.equal(cat.stats.physics_offerings,425);
for(const code of ['PHYS10002','PHYS10003','PHYS10004','PHYS10005','PHYS10006','PHYS10006h','PHYS20006','PHYS20010h','PHYS30012','AIS310013']){
  const g=groups.get(code);assert(g&&summaries.has(g.id),code);assert.equal(typeof g.student_evaluation.has_reviews,'boolean');
  assert(en.records.some(r=>r.course_ids.includes(g.id)&&r.snapshot_as_of==='2026-10-27'));
}
const b=groups.get('PHYS10003'),lower=groups.get('PHYS10004'),exp=groups.get('PHYS10005');
assert(b.direct_review_ids.concat(b.other_teacher_review_ids).includes(3178));
assert(!lower.direct_review_ids.concat(lower.other_teacher_review_ids).includes(3178));
for(const duplicate of [3906,3918])assert(!exp.direct_review_ids.includes(duplicate)&&exp.teacher_evidence.every(t=>!t.direct_review_ids.includes(duplicate)));
const mech=groups.get('PHYS10006');assert(mech.teacher_evidence.every(t=>!t.direct_review_ids.includes(247)));
const snap=en.records.filter(r=>r.snapshot_as_of==='2026-10-27');assert.equal(snap.length,425);
assert(snap.some(r=>r.limit_count===0)&&snap.some(r=>r.limit_count>0&&r.std_count>r.limit_count));
assert(!/@chatroom|wxid_|SAMLResponse|loginToken/.test(JSON.stringify(snap)));
const box={window:{},fetch:async()=>({ok:true,json:async()=>syn})};vm.runInNewContext(fs.readFileSync(path.join(p,'assets/course-synthesis.js'),'utf8'),box);
(async()=>{await box.window.CourseSynthesis.init();for(const code of ['PHYS10006','PHYS20006','PHYS30012','AIS310013']){
 const html=box.window.CourseSynthesis.summary(groups.get(code));assert(!/\[object Object\]|undefined/.test(html));}
 console.log(JSON.stringify({passed:'physics course and enrollment integration',physics_courses:95,physics_sections:425}));
})().catch(e=>{console.error(e);process.exitCode=1});
