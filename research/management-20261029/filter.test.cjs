const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const data=JSON.parse(fs.readFileSync(path.join(__dirname,'dataset.json'),'utf8'));
const html=fs.readFileSync(path.join(__dirname,data.department+'课程研究预览.html'),'utf8');
const decode=s=>s.replaceAll('&quot;','"').replaceAll('&#x27;',"'").replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&');
const cards=[...html.matchAll(/<details class="course"([^>]+)>/g)].map(m=>({dataset:Object.fromEntries([...m[1].matchAll(/data-([a-z]+)="([^"]*)"/g)].map(a=>[a[1],decode(a[2])])),hidden:false}));
const elements=Object.fromEntries(['q','plan','type','prefix','count'].map(id=>[id,{value:'',textContent:'',addEventListener(){}}]));
const context=vm.createContext({document:{getElementById:id=>elements[id],querySelectorAll:()=>cards}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const filter=()=>{vm.runInContext('filter()',context);return cards.filter(c=>!c.hidden)};
assert.equal(filter().length,data.courses.length);
for(const c of data.courses){elements.q.value=c.code;assert(filter().some(x=>x.dataset.search.includes(c.code.toLowerCase())));}
const sample=data.courses.find(c=>c.teachers.length&&c.search_aliases.length);
for(const term of [sample.name,sample.teachers[0],...sample.search_aliases]){elements.q.value=term;assert(filter().length>0,term);}
elements.q.value='__unique_body_text_not_name__';assert.equal(filter().length,0);
elements.q.value='';elements.prefix.value=cards[0].dataset.prefix;assert(filter().every(c=>c.dataset.prefix===elements.prefix.value));
elements.prefix.value='';const plan=cards.flatMap(c=>JSON.parse(c.dataset.plans)).find(p=>p!=='2026级 公共方案');assert(plan);elements.plan.value=plan;
assert(filter().length>0);assert(filter().every(c=>JSON.parse(c.dataset.plans).some(p=>p===plan||p==='2026级 公共方案')));
elements.plan.value='';elements.type.value=JSON.parse(cards.find(c=>JSON.parse(c.dataset.types).length).dataset.types)[0];assert(filter().every(c=>JSON.parse(c.dataset.types).includes(elements.type.value)));
elements.type.value='';assert.equal(filter().length,data.courses.length);
console.log(data.department+': code/name/teacher/pinyin, course type/prefix, public+major filters passed');
