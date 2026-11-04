from pathlib import Path
r=Path(__file__).resolve().parents[1];p=r/'public/app.js';s=p.read_text(encoding='utf-8')
s="import {auditState,executeTool,runAgent,comparePlans} from './agent.js';\nimport {parseTranscript} from './audit.js';\nimport {auditView,dualView} from './features.js';\n"+s
s=s.replace("completed:[]});","completed:[],englishTier:'B',development:'专业进阶路径',branches:{}});")
s=s.replace('course-compass-v1','course-compass-v2')
s=s.replace('let data,details,courses,byId;',"let data,details,courses,byId,publicPlan,major,apiKey='',activeSlot='A';\nconst agentState={profile:null,plans:{A:[],B:[]},planProfiles:{},records:[],recognitions:[],checks:{},allocations:{},history:[],trace:[]};\nfunction context(){agentState.profile=profile;agentState.plans[activeSlot]=selected;return {data,details,byId,publicPlan,major,state:agentState};}\n")
start=s.index('function persist()');end=s.index('function toast(',start)
s=s[:start]+"""function persist(){context();localStorage.setItem('course-compass-v2',JSON.stringify({profile,activeSlot,records:agentState.records,recognitions:agentState.recognitions,checks:agentState.checks,allocations:agentState.allocations,planProfiles:agentState.planProfiles,plans:Object.fromEntries(['A','B'].map(k=>[k,agentState.plans[k].map(i=>({course:i.course.id,section:i.section.id}))]))}));}
"""+s[end:]
s=s.replace("({workspace,explore,schedule,path:pathView,about}[view])()","({workspace,explore,schedule,path:pathView,audit:()=>auditView(context(),activeSlot),dual:()=>dualView(context(),activeSlot),about}[view])()")
s=s.replace("about:'项目与数据'}[view]","about:'项目与数据',audit:'学分审计',dual:'双方案比较'}[view]")
s=s.replace("function bind(){","function bind(){bindV2();")
s=s.replace("for(const id of ['plan-select','term-select','hours-input','completed-input','free-wed'])if($('#'+id))$('#'+id).onchange=capture;","for(const id of ['term-select','hours-input','completed-input','free-wed'])if($('#'+id))$('#'+id).onchange=capture; if($('#plan-select'))$('#plan-select').onchange=async()=>{capture();major=await fetch('data/plans/'+profile.plan+'.json').then(r=>r.json());agentState.history=[];render();};")
start=s.index('function generate()');end=s.index('function showCourse(',start)
s=s[:start]+"""function generate(){capture();const result=executeTool('build_plan',{slot:activeSlot},context());selected=agentState.plans[activeSlot];step=3;trace=[{tool:'真实教学班筛选与约束检查',result:`${result.metrics.courses} 门 · ${result.metrics.credits} 学分 · ${result.metrics.conflicts.length} 组冲突`}];messages.push({role:'assistant',text:`方案 ${activeSlot} 已生成：${result.metrics.courses} 门，${result.metrics.credits} 学分。公共＋专业审计已同步更新，可在双方案页比较或继续调整教师。`});persist();render();}
"""+s[end:]
start=s.index('async function sendChat(');end=s.index('function bind()',start)
s=s[:start]+"""async function sendChat(text){if(busy||!text.trim())return;capture();messages.push({role:'user',text});if(!apiKey){messages.push({role:'assistant',text:'可以用右侧条件生成候选、审计学分和比较 A/B。连接 DeepSeek 后，可在这里连续检索、生成并调整方案。'});render();return;}busy=true;render();try{const result=await runAgent(context(),text,callModel,{onTrace:event=>{trace.push({tool:event.tool,result:JSON.stringify(event.args)});const record=$('#chat-messages');if(record)record.setAttribute('aria-busy','true');}});profile=agentState.profile;selected=agentState.plans[activeSlot];messages.push({role:'assistant',text:result.answer});trace=result.trace.map(t=>({tool:t.tool,result:JSON.stringify(t.args)+' → '+(t.result?.error||'完成')}));step=3;persist();toast(`${result.trace.length} 次真实工具调用 · ${result.usage.total_tokens} tokens`);}catch(e){messages.push({role:'assistant',text:'本次连接：'+e.message+'。已完成的工具结果保留在方案中。'});}finally{busy=false;render();$('#chat-messages')?.scrollTo(0,99999);}}
async function callModel(payload){const r=await fetch('/api/model',{method:'POST',headers:{'Content-Type':'application/json','x-deepseek-key':apiKey},body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw Error(d.error||'模型连接失败');return d;}
"""+s[end:]
start=s.index("$('#settings-form').onsubmit=");end=s.index("try{[data,details]",start)
s=s[:start]+"""$('#settings-form').onsubmit=async e=>{e.preventDefault();apiKey=$('#api-key').value.trim();$('#api-key').value='';$('#settings-result').textContent='正在连接 DeepSeek…';try{const d=await callModel({messages:[{role:'user',content:'只回复连接成功，不调用工具。'}]});model=true;$('#model-status').textContent='DeepSeek Flash 已连接';$('#settings-result').textContent=d.choices[0].message.content||'连接成功';render();}catch(e){apiKey='';model=false;$('#settings-result').textContent=e.message;}};
$('#disconnect').onclick=()=>{apiKey='';model=false;agentState.history=[];$('#model-status').textContent='本地规划模式';$('#settings-result').textContent='密钥与模型会话已清除';render();};
window.addEventListener('pagehide',()=>{apiKey='';});
function download(name,value,type='application/json'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([typeof value==='string'?value:JSON.stringify(value,null,2)],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function bindV2(){
 if($('#apply-transcript'))$('#apply-transcript').onclick=()=>{const result=parseTranscript($('#transcript').value,courses);if(result.errors.length){$('#transcript-result').textContent=result.errors.join('；');return;}agentState.records=result.records;profile.completed=result.records.filter(r=>r.status==='passed').map(r=>r.code);agentState.history=[];persist();render();toast('修读记录与审计已更新');};
 if($('#sample-transcript'))$('#sample-transcript').onclick=()=>{$('#transcript').value='MATH10020,4,已通过,2025秋\\nMATH30011,3,预选,2026春';toast('这是演示记录；点击保存后用于本次测试');};
 for(const [id,key] of [['english-tier','englishTier'],['development','development']])if($('#'+id))$('#'+id).onchange=e=>{profile[key]=e.target.value;persist();render();};
 document.querySelectorAll('[data-audit-check]').forEach(b=>b.onchange=()=>{agentState.checks[b.dataset.auditCheck]=b.checked;persist();render();});
 document.querySelectorAll('[data-allocation]').forEach(b=>b.onchange=()=>{agentState.allocations[b.dataset.allocation]=b.value;persist();render();});
 document.querySelectorAll('[data-branch]').forEach(b=>b.onchange=()=>{profile.branches[b.dataset.branch]=b.value;persist();render();});
 if($('#add-recognition'))$('#add-recognition').onclick=()=>{const from=$('#recognition-from').value.trim(),to=$('#recognition-to').value.trim();if(!from||!to)return toast('请填写原课与替代课代码');agentState.recognitions.push({from,to,confirmed:true});persist();render();};
 document.querySelectorAll('[data-recognition-remove]').forEach(b=>b.onclick=()=>{agentState.recognitions.splice(Number(b.dataset.recognitionRemove),1);persist();render();});
 if($('#export-audit'))$('#export-audit').onclick=()=>download('课途_完整学分审计.json',auditState(context(),activeSlot));
 if($('#build-ab'))$('#build-ab').onclick=()=>{context();executeTool('build_plan',{slot:'A'},context());executeTool('build_plan',{slot:'B',goal:'balanced',max_credits:Math.max(6,profile.maxCredits-2),free_wednesday:true},{data,details,byId,publicPlan,major,state:agentState});selected=agentState.plans[activeSlot];persist();render();};
 document.querySelectorAll('[data-active-slot]').forEach(b=>b.onclick=()=>{context();activeSlot=b.dataset.activeSlot;selected=agentState.plans[activeSlot];persist();render();});
 document.querySelectorAll('[data-clone-slot]').forEach(b=>b.onclick=()=>{context();const from=b.dataset.cloneSlot,to=from==='A'?'B':'A';agentState.plans[to]=[...agentState.plans[from]];agentState.planProfiles[to]={...agentState.planProfiles[from]};selected=agentState.plans[activeSlot];persist();render();});
}
"""+s[end:]
s=s.replace("[data,details]=await Promise.all(['catalog','details'].map(n=>fetch('data/'+n+'.json').then(r=>r.json())));","[data,details,publicPlan,major]=await Promise.all(['data/catalog.json','data/details.json','data/plans/466.json','data/plans/'+profile.plan+'.json'].map(n=>fetch(n).then(r=>r.json())));")
start=s.index("try{const saved=JSON.parse(localStorage",s.index('try{[data,details'))
end=s.index("render();}catch(e)",start)
s=s[:start]+"""try{const saved=JSON.parse(localStorage.getItem('course-compass-v2')||'null');if(saved){activeSlot=saved.activeSlot||'A';for(const k of ['records','recognitions','checks','allocations','planProfiles'])if(saved[k])agentState[k]=saved[k];for(const k of ['A','B'])agentState.plans[k]=(saved.plans?.[k]||[]).map(s=>({course:byId[s.course],section:details[s.course]?.sections.find(i=>i.id===s.section)})).filter(i=>i.course&&i.section);selected=agentState.plans[activeSlot];}}catch{}$('#api-base').value='https://api.deepseek.com';$('#api-model').value='deepseek-flash';model=false;"""+s[end:]
s=s.replace('DeepSeek Flash · 检索课程证据后作答','DeepSeek Flash · 多轮工具调用')
s=s.replace('<li>将公共与专业方案的学分规则转成完整的学业进度审计。</li>','<li>公共＋专业规则已接入学分、门数、必修与分支审计。</li>')
s=s.replace('<li>增加多目标搜索与 A/B 方案、模型结构化工具调用。</li>','<li>A/B 独立方案、真实多轮工具调用与逐周时间对比已接入。</li>')
s=s.replace('面向参赛的下一步','学业规划与后续扩展')
p.write_text(s,encoding='utf-8')
h=r/'public/compass.html';x=h.read_text(encoding='utf-8');x=x.replace('<button data-view="path">','<button data-view="audit"><span>✓</span>学分审计</button><button data-view="dual"><span>⇄</span>双方案比较</button><button data-view="path">');x=x.replace('交互初稿 01','规划工作版 02');x=x.replace('仅保存在本次本地服务内存','仅在当前页面内存保存');x=x.replace('测试 API Key','你的 DeepSeek API Key');x=x.replace('调用经过本机服务转发。发送的内容包括当前问题、学习偏好与匹配课程摘要。','密钥只用于当前页面会话，经站点服务转发至 DeepSeek 官方接口。刷新或清除连接后失效。模型会读取问题、修读记录及匹配课程证据。');x=x.replace('id="api-base" type="url"','id="api-base" readonly type="url"').replace('id="api-model" value=','id="api-model" readonly value=');h.write_text(x,encoding='utf-8')
