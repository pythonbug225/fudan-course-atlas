const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../public'),read=n=>require('../scripts/read-catalog.cjs')(path.join(root,'data',n+'.json'));
const c=read('catalog'),r=read('github-sync'),s=read('review-supplement'),f=read('full-discussions'),syn=read('course-summaries'),q=read('search');
assert.equal(r.source_commit,'cb938beb81e2590bcb6ee5c6cc3fc36aa4589a4c');
assert.deepEqual(r.incoming_syllabi,{body:580,template_error:154,blank_template:7});
assert.equal(r.bindings.length,578);assert.equal(r.conflicts.length,2);assert.equal(r.counts.inline_2026_plans,37);
const byId=new Map(c.scope.map(g=>[g.id,g]));assert.equal(byId.size,c.scope.length);
const sy=new Map(c.syllabi.map(s=>[String(s.lesson_id),s]));
for(const b of r.bindings){
 const g=byId.get(b.course_id),o=g.offerings.find(o=>o.term===b.term&&o.code===b.section);assert(o);
 assert.deepEqual([...o.teachers].sort(),[...b.teachers].sort());assert.equal(String(o.syllabus),b.syllabus_id);
 const doc=sy.get(b.syllabus_id);assert(doc&&!doc.summary_only&&doc.original_sha256===b.sha256);
 const text=fs.readFileSync(path.join(root,doc.href),'utf8');assert(text.includes(g.name));assert(!/FreeMarker|Java stack trace|<script|@chatroom|wxid_|SAMLResponse|loginToken/.test(text));
}
for(const conflict of r.conflicts){assert.equal(conflict.reason,'教师名单不同，仅作来源版本资料，不覆盖本班大纲');const g=c.scope.find(g=>g.code===conflict.code);const o=g.offerings.find(o=>o.term===conflict.term&&o.code===conflict.section);assert.deepEqual(o.teachers,conflict.offering_teachers);}
for(const id of r.historical_course_ids){const g=byId.get(id);assert(g.history_only&&g.offerings.length===0&&g.student_evaluation.has_reviews);assert(q.entries[id]?.fields.includes(g.code.toLowerCase()));assert(syn.records.some(x=>x.id===id));}
const records=s.records.filter(x=>x.batch==='20261031-medical');assert.equal(records.length,r.review_audit.adopted_new);assert.equal(new Set(records.map(x=>x.source_id)).size,records.length);
for(const x of records){assert(x.summary&&x.source_label&&x.term);assert(!x.source_url);assert(!x.source_id.endsWith(':2133'));assert(x.scope_label.includes('历史'));assert(x.full_original);assert(f.records[x.id]?.floors.length);}
for(const [id,hash]of Object.entries(r.review_original_sha256)){const text=f.records[id].floors.map(x=>x.text).join('\n');assert.equal(crypto.createHash('sha256').update(text).digest('hex'),hash);assert(!/wxid_|@chatroom|alter_by|reviewer_id|loginToken/.test(text));}
assert(!/alter_by|reviewer_id|xsec_token|SAMLResponse|loginToken/.test(JSON.stringify(records)));
console.log('GitHub delta, medical syllabus identity, empty-file exclusion, plan versions, historical reviews and original text hashes passed.');
