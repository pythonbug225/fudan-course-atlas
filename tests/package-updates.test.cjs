const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../public'),read=n=>JSON.parse(fs.readFileSync(path.join(root,'data',n+'.json'),'utf8'));
const cat=read('catalog'),sup=read('review-supplement'),report=read('package-updates'),full=read('full-discussions'),search=read('search'),summary=read('course-summaries');
const select={innerHTML:''},box={D:cat,document:{querySelector:()=>select}};vm.runInNewContext(fs.readFileSync(path.join(root,'assets/taxonomy.js'),'utf8')+';this.api=CourseTaxonomy;',box);box.api.init(cat);
for(const [key,label,count] of [['economics','经济专业',301],['management','管理专业',267],['philosophy','哲学专业',267],['law','法学专业',260],['wenbo','文博专业',133],['tourism','旅游管理专业',85],['psychology','心理学专业',88],['sport','运动训练专业',43]]){
 assert(select.innerHTML.includes(`value="${key}"`));assert.equal(cat.scope.filter(g=>box.api.match(g,key)).length,count);assert(cat.scope.some(g=>g.categories.includes(label)&&search.entries[g.id]));
}
const medicineFile=path.join(root,'data/medicine-update.json'),medicine=fs.existsSync(medicineFile)?read('medicine-update'):null;
const latest=read('latest-update');assert.equal(cat.scope.length,latest.total_courses);assert.equal(cat.scope.reduce((n,g)=>n+g.offerings.length,0),latest.total_sections);assert.equal(cat.syllabi.length,latest.total_syllabi);
for(const [id,sha] of Object.entries(report.new_originals)){const r=sup.records.find(r=>r.id===id);assert(r?.full_original);assert.equal(crypto.createHash('sha256').update(full.records[id].floors[0].text).digest('hex'),sha);}
assert(report.source_packages.length===6);assert(report.source_packages.every(p=>p.updated_at&&/^[a-f0-9]{64}$/.test(p.sha256)));
const snippets=sup.records.filter(r=>r.batch==='20261030-github');assert.equal(snippets.length,720);assert(snippets.filter(r=>r.discussion_only).every(r=>r.scope_label.includes('非修读评价')));
assert(snippets.every(r=>!r.source_url||/^https:\/\/(?:www\.)?(?:zhihu|xiaohongshu)\.com\//.test(r.source_url)));
const archaeology=cat.scope.find(g=>g.code==='ARCH10001');assert(archaeology&&search.entries[archaeology.id].fields.includes('kgxdl'));assert(archaeology.offerings.some(o=>o.department==='文物与博物馆学系'&&o.credits===2));
const law=cat.scope.find(g=>g.categories.includes('法学专业')&&!g.student_evaluation.has_reviews);assert(law);assert(summary.records.some(r=>r.id===law.id));
for(const p of report.local_materials){assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p.path))).digest('hex'),p.sha256);}
const sources=new Set(snippets.map(r=>r.source_id));assert(sup.sources.filter(s=>sources.has(s.id)).every(s=>s.record_ids.every(id=>sup.records.some(r=>r.id===id))));
console.log('Package update timestamps, verified originals, department filters, exact course mapping and materials integrity passed.');
