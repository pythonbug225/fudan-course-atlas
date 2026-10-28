const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../public'),read=f=>JSON.parse(fs.readFileSync(path.join(root,'data',f),'utf8'));
const cat=read('catalog.json'),reviews=read('review-supplement.json'),search=read('search.json');
const groups=new Map(cat.scope.map(g=>[g.id,g])),select={innerHTML:''};
const box={D:cat,document:{querySelector:()=>select}};
vm.runInNewContext(fs.readFileSync(path.join(root,'assets/taxonomy.js'),'utf8')+'\nthis.api=CourseTaxonomy;',box);
box.api.init(cat);
for(const [key,label] of [['chinese','中文专业'],['sirpa','国务专业'],['foreign','外语专业'],['chemistry','化学专业'],['biology','生命科学专业'],['environment','环境科学专业'],['biomed','生物医学工程']]){
 assert(select.innerHTML.includes(`value="${key}"`));
 const course=cat.scope.find(g=>g.categories.includes(label));assert(course&&box.api.match(course,key),label);
}
const chinese=cat.scope.find(g=>g.code==='CHIN00001');assert(chinese&&chinese.offerings.some(o=>o.term==='2025秋'&&o.code==='CHIN00001.01'));
assert(cat.scope.find(g=>g.code==='CHIN10005').plan_refs.length>0);assert(reviews.records.some(r=>r.course_ids.includes(chinese.id)&&/旦夕课评/.test(r.source_type)));
assert(reviews.materials.some(m=>m.course_ids.includes(chinese.id)&&m.title==='传统文化阅读与鉴赏'));
const syllabus=cat.syllabi.find(s=>s.lesson_id===1004714);assert(syllabus&&syllabus.summary_only&&syllabus.assessment.some(a=>a.percentage===70));
assert(fs.existsSync(path.join(root,syllabus.href)));
const english=cat.scope.find(g=>g.code==='FORE10024');assert(english&&search.entries[english.id].fields.includes('fycjst'));
assert(cat.plans.some(p=>p.title.includes('智能机器人与先进制造创新学院')));
assert(cat.plans.some(p=>p.title.includes('环境科学与工程系')));assert(cat.plans.some(p=>p.title.includes('生命科学学院')));
const biomed=cat.scope.find(g=>g.code==='BME50021');assert(biomed&&biomed.history_only&&biomed.offerings.length===0&&biomed.plan_credits===2);
assert(reviews.records.filter(r=>r.course_ids.includes(biomed.id)&&r.id.startsWith('collab_')).length===2);
assert(cat.scope.some(g=>g.id.startsWith('COLLAB_')&&g.student_evaluation.has_reviews===false));
for(const r of reviews.records.filter(r=>r.id.startsWith('collab_'))){assert(r.course_ids.every(id=>groups.has(id)));assert(!/官方大纲结构摘要/.test(r.summary));}
console.log('Collaborator course, category, provenance, plan, syllabus and search checks passed.');
