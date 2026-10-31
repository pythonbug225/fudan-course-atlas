const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),vm=require('node:vm');
const root=path.resolve(__dirname,'../public'),read=n=>require('../scripts/read-catalog.cjs')(path.join(root,'data',n+'.json'));
const c=read('catalog'),r=read('nonmedical-update'),s=read('review-supplement'),search=read('search'),syn=read('course-summaries'),en=read('enrollment'),full=read('full-discussions');
assert.equal(r.official_nonmedical_sections,12661);assert.equal(r.matched_official_sections,r.official_nonmedical_sections);
assert.deepEqual(r.conflicts,[]);assert.deepEqual(r.syllabus_conflicts,[]);
assert.equal(c.scope.length,r.totals.courses);assert.equal(c.syllabi.length,r.totals.syllabi);assert.equal(c.scope.reduce((n,g)=>n+g.offerings.length,0),r.totals.sections);
assert.equal(r.plan_files.length,342);assert.equal(r.plan_files.filter(p=>p.status==='full_document').length,341);
for(const p of r.plan_files){const bytes=fs.readFileSync(path.join(root,p.href));assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),p.sha256);assert(c.plans.some(x=>x.plan_id===p.plan_id&&x.href===p.href));}
assert.equal(r.plan_files.find(x=>x.plan_id===151832).status,'course_index_only');assert.notEqual(r.plan_files.find(x=>x.plan_id===152715).href,r.plan_files.find(x=>x.plan_id===151991)?.href);
const newIds=new Set(r.new_course_ids),summaries=new Map(syn.records.map(x=>[x.id,x]));
for(const x of syn.records)assert.equal(typeof x.card,'string');
for(const x of syn.records)assert(x.card.trim(),x.id+' requires a readable card summary');
for(const x of syn.records)for(const [term,t]of Object.entries(x.term_summaries||{})){assert.equal(typeof(t.card||t.overview),'string',x.id+' '+term);assert((t.card||t.overview).trim());for(const ref of t.source_refs||[])assert(syn.sources[ref],ref);for(const teacher of t.by_teacher||[])assert.equal(typeof teacher.summary,'string');}
for(const g of c.scope.filter(g=>newIds.has(g.id))){assert(search.entries[g.id]?.fields.length,g.code);assert(summaries.has(g.id));assert.equal(typeof g.student_evaluation.has_reviews,'boolean');if(!g.student_evaluation.has_reviews)assert(g.student_evaluation.label);for(const o of g.offerings){assert(o.department);assert(Number.isFinite(o.credits));assert(!/临床医学院|公共卫生学院|护理学院|口腔医学院|法医学/.test(o.department));}}
for(const y of c.syllabi.filter(y=>y.href?.startsWith('syllabi/nonmedical-20261030-'))){assert.equal(typeof y.summary_only,'boolean');assert(fs.existsSync(path.join(root,y.href)));const offers=c.scope.flatMap(g=>g.code===y.course_code?g.offerings:[]);assert(offers.some(o=>o.term===y.term&&o.code===y.section_code&&o.teachers.join('|')===y.teachers.join('|')),y.title);}
for(const x of s.records.filter(x=>x.batch==='20261030-nonmedical')){assert(x.summary&&x.source_label&&x.term);if(x.source_url)assert(/^https:\/\/(?:www\.)?(?:zhihu|xiaohongshu)\.com\//.test(x.source_url));if(x.full_original)assert(full.records[x.id]?.floors.every(f=>f.text));}
for(const [id,hash]of Object.entries(r.new_original_hashes||{}))assert.equal(crypto.createHash('sha256').update(full.records[id].floors.map(x=>x.text).join('\n')).digest('hex'),hash);
for(const x of en.records){assert(x.limit_count===null||Number.isInteger(x.limit_count)&&x.limit_count>=0);}
const box={D:c,document:{querySelector:()=>({innerHTML:''})}};vm.runInNewContext(fs.readFileSync(path.join(root,'assets/taxonomy.js'),'utf8')+';this.api=CourseTaxonomy;',box);
for(const [type,label]of [['robotics','机器人与制造专业'],['materials-energy','智能材料与能源专业'],['future-info','未来信息专业'],['ic','集成电路专业']]){const g=c.scope.find(g=>g.categories.includes(label));assert(g&&box.api.match(g,type));}
assert(!/wxid_|@chatroom|xsec_token|SAMLResponse|loginToken/.test(JSON.stringify(r)));
for(const item of read('offsite-assets').assets){
 assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,item.path))).digest('hex'),item.sha256);
 assert(item.url.startsWith('https://github.com/pythonbug225/fudan-course-atlas/releases/download/nonmedical-completion-20261031/')||/^https:\/\/raw\.githubusercontent\.com\/pythonbug225\/fudan-course-atlas\/[a-f0-9]{40}\/public\/assets\//.test(item.url));
 assert(!fs.readFileSync(path.join(root,'_redirects'),'utf8').split('\n').some(line=>line.trim()&&!line.trim().startsWith('#')));
}
console.log('Nonmedical plans, official classes, original reviews, identity joins and resources verified.');
