const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../public');const read=n=>require('../scripts/read-catalog.cjs')(path.join(root,'data',n+'.json'));
const cat=read('catalog'),sup=read('review-supplement'),full=read('full-discussions'),en=read('enrollment'),search=read('search');
const select={innerHTML:''},box={D:cat,document:{querySelector:()=>select}};
vm.runInNewContext(fs.readFileSync(path.join(root,'assets/taxonomy.js'),'utf8')+';this.taxonomy=CourseTaxonomy;',box);box.taxonomy.init(cat);
for(const [key,label,count] of [['atmosphere','大气与海洋专业',73],['nuclear','核科学专业',52],['polymer','高分子专业',59],['biotech','生物技术专业',54],['bigdata','大数据专业',84]]){
 const groups=cat.scope.filter(g=>box.taxonomy.match(g,key));assert.equal(groups.length,count);assert(select.innerHTML.includes(`value="${key}"`));assert(groups.every(g=>g.categories.includes(label)&&search.entries[g.id]));
}
const course=code=>cat.scope.find(g=>g.code===code);
const intro=course('ATMO10001');assert(search.entries[intro.id].fields.includes('dqkxdl'));assert(intro.offerings.some(o=>o.term==='2025秋'&&o.credits===2&&o.teachers.includes('张若楠')));
assert(en.records.some(r=>r.course_ids.includes(intro.id)&&r.section_code==='ATMO10001.01'&&r.std_count===45&&r.limit_count===55));
const ocean=course('ATMO20005');assert(sup.materials.some(m=>m.course_ids.includes(ocean.id)&&m.url==='https://corp.fudan.edu.cn/index_education.htm'));
assert(cat.syllabi.some(s=>s.course_code==='STAT20011'&&!s.summary_only&&fs.existsSync(path.join(root,s.href))));
const added=sup.records.filter(r=>r.id.startsWith('dept29_'));assert(added.length>200);
assert(added.filter(r=>r.full_original).every(r=>full.records[r.id]?.floors.every(f=>f.text&&f.author_label)));
const questions=added.filter(r=>r.discussion_only);assert(questions.length>0&&questions.every(r=>/非修读评价/.test(r.scope_label)));
assert(sup.materials.some(m=>m.url?.endsWith('fudan-bigdata-20261029.zip')));assert(sup.materials.some(m=>m.url?.endsWith('four-colleges-course-research-20261029.zip')));
assert(cat.plans.some(p=>/2026/.test(p.title)&&/生物技术/.test(p.title)));assert(cat.plans.some(p=>/2026/.test(p.title)&&/大气科学/.test(p.title)));
const ui={window:{},URL,encodeURIComponent,document:{addEventListener(){}},fetch:async u=>({ok:true,json:async()=>read(u.replace(/^data\//,'').replace(/\.json$/,''))})};
ui.ReviewSupplement={sourceLinks:()=>''};
vm.runInNewContext(fs.readFileSync(path.join(root,'assets/review-reader.js'),'utf8'),ui);
(async()=>{await ui.window.ReviewReader.init(cat);const r=added.find(r=>r.full_original&&r.teacher_names.length),g=cat.scope.find(g=>g.id===r.course_ids[0]);const rendered=ui.window.ReviewReader.render(g,r.teacher_names[0]);assert(rendered.includes(full.records[r.id].floors[0].text.slice(-35).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))));assert(!ui.window.ReviewReader.render(g,'不存在的教师').includes(full.records[r.id].floors[0].text));console.log('Five department categories, exact section counts, pinyin, materials and complete original rendering passed.');})().catch(e=>{console.error(e);process.exitCode=1});
