const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../public'),data=JSON.parse(fs.readFileSync(root+'/data/review-supplement.json','utf8')),cat=JSON.parse(fs.readFileSync(root+'/data/catalog.json','utf8'));
let passed=0;const ok=(v,m)=>{assert.ok(v,m);passed++};const ids=new Set(cat.scope.map(g=>g.id));
ok(new Set(data.records.map(r=>r.id)).size===data.records.length,'record IDs unique');
const serverIds=JSON.parse(fs.readFileSync(path.join(root,'../lib/course-ids.json'),'utf8'));ok(serverIds.length===ids.size&&serverIds.every(id=>ids.has(id)),'public catalog and upload API share the same course list');
const coverage=JSON.parse(fs.readFileSync(root+'/data/research-coverage.json','utf8'));
ok(coverage.courses.length===ids.size&&new Set(coverage.courses.map(g=>g.id)).size===ids.size,'every course has a reading status');
for(const g of coverage.courses){ok(g.read_direct_reviews+g.unread_direct_reviews===g.direct_reviews,'reading counts reconcile '+g.id);ok(g.teachers.every(t=>t.read_reviews<=t.direct_reviews),'teacher reading counts are bounded')}
const chats=data.records.filter(r=>r.id.startsWith('chat'));
ok(chats.length>0&&chats.every(r=>/年级群/.test(r.source_label)&&!r.source_url),'private chats have source labels and no archive links');
ok(chats.every(r=>!/@chatroom|wxid_|accountName|sender|拍了拍|\b1[3-9]\d{9}\b/.test(JSON.stringify(r))),'private group identity never enters public reviews');
ok(chats.every(r=>!/贾若桐|印佳/.test(JSON.stringify(r))),'private student TA names are anonymized in all displayed fields');
const du=data.records.find(r=>r.id==='chat26_du_2026_assessment');ok(du&&du.teacher==='杜恺'&&du.course_ids.join()==='C0040'&&/2026秋/.test(du.term)&&/70%/.test(du.assessment)&&/30%/.test(du.assessment),'new Du assessment remains attached to the correct teacher, H course and term');
for(const r of data.records){ok(r.course_ids.length>0&&r.course_ids.every(i=>ids.has(i)),'valid course mapping '+r.id);ok(r.source_id&&r.source_label&&r.summary&&r.judgment,'provenance and synthesis '+r.id);const text={...r};delete text.source_url;ok(!/https?:|xsec_token|data:image|<script|@m\.fudan/.test(JSON.stringify(text)),'public prose contains no token, raw image or login identity '+r.id);if(r.source_url){const u=new URL(r.source_url);ok(['https:','http:'].includes(u.protocol)&&!u.search&&!u.hash&&!u.username&&!u.password,'canonical reference link '+r.id)}for(const x of r.source_excerpts||[])ok(x.label&&x.text.length<=150,'brief labelled original extract '+r.id)}
const box={window:{},fetch:async()=>({ok:true,json:async()=>data})};vm.runInNewContext(fs.readFileSync(root+'/assets/review-supplement.js','utf8'),box);
(async()=>{const t=box.window.ReviewSupplement;await t.init();
const quantum=cat.scope.find(g=>g.code==='PHYS40012');
for(const teacher of ['肖江','吴长勤'])ok(t.materials(quantum,teacher).includes('复旦在线课程门户'),'historical shared teaching resource visible to '+teacher);
ok(!t.materials(quantum,'其他教师').includes('复旦在线课程门户'),'shared resource stays scoped to its teacher team');
const lowTemperature=cat.scope.find(g=>g.code==='PHYS70008');
ok(t.materials(lowTemperature,'李炜').includes('低温和超导物理：课程教学提纲'),'faculty course outline remains attached to its teacher');
ok(!t.materials(lowTemperature,'其他教师').includes('低温和超导物理：课程教学提纲'),'faculty course outline is not attributed to other teachers');
for(const g of cat.scope){const rows=t.select(g);ok(rows.every(r=>r.course_ids.includes(g.id)),'scoped records');for(const teacher of t.teachers(g)){const filtered=t.select(g,teacher);ok(filtered.every(r=>!r.teacher||r.teacher===teacher||(r.teacher_names||[]).includes(teacher)),'parallel teachers separated')}
ok(!/<a\b/.test(t.summary(g,'all')),'summary remains source text only');const html=t.comments(g,'all');ok((html.match(/<a\b/g)||[]).length===(html.match(/data-review-source="public"/g)||[]).length,'only marked public source anchors in reviews')}
const math=cat.scope.find(g=>g.id==='C0055');ok(!t.select(math).some(r=>r.course_ids.includes('U1694')),'statistics H not merged into mathematics statistics');
ok(t.select(cat.scope.find(g=>g.id==='C0039'),'吴昊').some(r=>r.id==='zhihu_wu'),'Zhihu teacher match');ok(!t.select(cat.scope.find(g=>g.id==='C0039'),'梁振国').some(r=>r.id==='zhihu_wu'),'parallel teacher exclusion');
ok(t.comments(cat.scope.find(g=>g.id==='C0040'),'楼红卫').includes('知乎助教教学说明'),'TA observations identified separately');ok(!t.comments(cat.scope.find(g=>g.id==='C0040'),'杜恺').includes('zhihu_luni_ta'),'TA class is not assigned to another teacher');
ok(t.comments(cat.scope.find(g=>g.id==='H0001'),'侯体健').includes('查看来源短摘'),'historical course shows newly collected original excerpts');
ok(data.sources.length===new Set(data.sources.map(s=>s.id)).size,'source identifiers unique');ok(data.stats.supplement_records===data.records.length&&cat.stats.supplement_records===data.records.length,'displayed counts agree');
console.log(JSON.stringify({passed,records:data.records.length,courses:data.stats.courses}));})();
