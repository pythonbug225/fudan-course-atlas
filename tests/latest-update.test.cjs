const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../public'),read=n=>JSON.parse(fs.readFileSync(path.join(root,'data',n+'.json'),'utf8'));
const c=read('catalog'),r=read('latest-update'),s=read('review-supplement'),f=read('full-discussions'),q=read('search'),syn=read('course-summaries');
const select={innerHTML:''},box={D:c,document:{querySelector:()=>select}};vm.runInNewContext(fs.readFileSync(path.join(root,'assets/taxonomy.js'),'utf8')+';this.api=CourseTaxonomy;',box);box.api.init(c);
for(const [key,label] of [['history','历史专业'],['ices','国交课程'],['ssdpp','社政专业'],['journalism','新闻专业'],['marxism','马克思主义理论专业']]){
 assert(select.innerHTML.includes(`value="${key}"`));assert.equal(c.scope.filter(g=>box.api.match(g,key)).length,r.domain_groups[key]);
 for(const g of c.scope.filter(g=>g.categories.includes(label))){assert(q.entries[g.id]);assert(syn.records.some(x=>x.id===g.id));}
}
const batch=s.records.filter(x=>x.batch==='20261030-latest');assert.equal(batch.length,r.counts.evaluation_records+r.counts.discussion_records);
assert.equal(new Set(batch.map(x=>x.id)).size,batch.length);assert.equal(r.conflicts.length,0);
assert.equal(c.scope.length,4838+r.counts.new_courses);assert.equal(c.scope.reduce((n,g)=>n+g.offerings.length,0),10882+r.counts.new_offerings);assert.equal(c.syllabi.length,5430+r.counts.full_syllabi);
for(const [id,hash] of Object.entries(r.new_originals)){const x=s.records.find(x=>x.id===id);assert(x.full_original);assert.equal(crypto.createHash('sha256').update(f.records[id].floors.map(x=>x.text).join('\n')).digest('hex'),hash);assert(f.records[id].license==='CC BY 4.0');}
assert.equal(Object.keys(r.new_originals).length,82);assert(r.source_branches.every(b=>b.updated_at&&/^[a-f0-9]{40}$/.test(b.commit)&&!b.root));
const newHtml=c.syllabi.filter(x=>String(x.local_html||x.html||x.path||'').includes('departments-20261029-'));
for(const g of c.scope.filter(g=>g.id.startsWith('COLLAB_')&&!g.student_evaluation?.has_reviews))assert(g.student_evaluation.label);
assert(!/wxid_|@chatroom|xsec_token|SAMLResponse|loginToken|D:\\\\/.test(JSON.stringify(r)));
console.log('Latest department filters, incremental totals, originals, source timestamps and missing-review labels passed.');
