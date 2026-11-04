const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.join(__dirname,'..','public');
const read=name=>require('../scripts/read-catalog.cjs')(path.join(root,'data',name));
const cat=read('catalog.json'),syn=read('course-summaries.json'),discussions=read('full-discussions.json'),supp=read('review-supplement.json');
const byCode=new Map(cat.scope.map(g=>[g.code,g]));
assert.equal(cat.stats.caic_course_groups,273);
assert.equal(cat.stats.caic_offerings,680);
assert.equal(cat.plans.filter(p=>p.title.startsWith('2026级 计智学院 · ')).length,18);
for(const p of cat.plans.filter(p=>p.title.startsWith('2026级 计智学院 · ')))assert.ok(fs.existsSync(path.join(root,p.href)),p.href);
for(const code of ['AIB110002','AIB310003','CS30042','CS30019']){
 const g=byCode.get(code);assert.ok(g,code);
 const summary=syn.records.find(r=>r.id===g.id);assert.ok(summary,code);
 assert.ok(summary.term_summaries?.['2026春']||summary.scope_term==='2026春',code);
}
assert.ok(byCode.get('AIB110002').offerings.some(o=>o.term==='2025秋'));
assert.ok(!cat.syllabi.some(s=>s.lesson_id===1020826));
assert.ok(!cat.scope.flatMap(g=>g.offerings).some(o=>o.syllabus===1020826));
assert.ok(!JSON.stringify(syn).includes('syllabus:1020826'),'mismatched syllabus excluded from every summary source');
assert.ok(!JSON.stringify(syn.records.find(r=>r.id==='C0629')).includes('研讨30%、汇报60%'),'misreturned assessment removed from historical profile');
const f6=supp.records.find(r=>r.id==='OTHER_CS_007');
assert.ok(f6&&f6.course_ids.includes(byCode.get('CS30019').id));
assert.ok(!f6.course_ids.includes(byCode.get('CS30069').id));
assert.equal(cat.reviews.find(r=>r.id===6294)?.teacher,'马晨曦');
assert.ok(byCode.get('CS30019').direct_review_ids.includes(6294));
assert.ok(!byCode.get('CS30069').direct_review_ids.includes(6294));
assert.equal(cat.reviews.find(r=>r.id===6600)?.teacher,'吴毅坚');
assert.ok(Object.values(discussions.records).some(r=>r.floors.some(f=>f.floor_id===6139081&&f.text.length>1000)));
assert.ok(supp.records.some(r=>r.id==='discussion_F592174-AIE310008-2026S'&&r.course_ids.includes(byCode.get('AIE310008').id)));
assert.ok(discussions.records['discussion_F592174-AIE310008-2026S'].floors.some(f=>f.floor_id===6167941&&f.text.length>1000));
const added=Object.entries(discussions.records).filter(([k])=>/^(caic_nova_|discussion_(FPA-|PB|FNT|F592174|F671219))/.test(k));
for(const [id,record] of added)for(const floor of record.floors)assert.ok(!/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\d)1[3-9]\d{9}(?!\d)|(?:微信号?|wx|wechat|vx)\s*[:：]\s*[A-Za-z0-9_-]{4,}/i.test(floor.text),'contact details removed: '+id);
for(const [code,floorId] of [['CS10003',6199794],['CS30043',6147198]]){
 const cid=byCode.get(code).id;
 const hits=supp.records.filter(r=>r.course_ids.includes(cid)&&discussions.records[r.id]?.floors.some(f=>f.floor_id===floorId));
 assert.equal(hits.length,1,'one original floor per course: '+code);
}
for(const r of cat.reviews)assert.ok(!/pan\.baidu\.com|\bpwd=[A-Za-z0-9_-]+/i.test(r.content||''),'no share-code link in review prose');
for(const source of cat.sharing)for(const file of source.files||[])assert.ok(!/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:密码|提取码|访问码)\s*[:：=]?\s*[A-Za-z0-9]{3,30}/i.test(file.name||''),'file labels redact personal or access details');
assert.ok(fs.existsSync(path.join(root,'assets','caic-plans-2026.zip')));
assert.ok(fs.readFileSync(path.join(root,'index.html'),'utf8').includes('<option>2025秋</option>'));
console.log('CAIC integration checks passed');
