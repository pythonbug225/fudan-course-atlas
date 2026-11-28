// 课途 · “帮我挑老师”页面
import {CRITERIA,LEVELS,DAYS,defaultPrefs,cleanPrefs,parseRequest,matchCourse,rankTeachers,bestCombos,describeSlots,candidateSections} from './picker.js';
import {parseSchedule,conflicts} from './engine.js';

const KEY='course-compass-picker-v1';
const EXAMPLES=['数理统计、大学物理B(下)，不点名，期末占比小，不要早八','羽毛球、学术英语(科学技术)，必须不点名，不要pre，周五空出来','线性代数，考试占比大，有学生课评的老师，不要晚课'];

let st=load();
function load(){
 try{const v=JSON.parse(localStorage.getItem(KEY)||'null');if(v&&typeof v==='object')return {text:typeof v.text==='string'?v.text.slice(0,600):'',courseIds:Array.isArray(v.courseIds)?v.courseIds.filter(x=>typeof x==='string').slice(0,12):[],prefs:cleanPrefs(v.prefs),parsed:null,result:null,query:''};}catch{}
 return {text:'',courseIds:[],prefs:defaultPrefs(),parsed:null,result:null,query:''};
}
function save(){try{localStorage.setItem(KEY,JSON.stringify({text:st.text,courseIds:st.courseIds,prefs:st.prefs}));}catch{}}

const statusIcon={good:'✓',bad:'✗',mixed:'≈',unknown:'?'};
function badge(env,c){return `<span class="pk-badge ${c.status}" title="${env.esc(c.detail)}">${statusIcon[c.status]} ${env.esc(c.label)}</span>`;}
function timeText(section){const p=parseSchedule(section.schedule||'');return p.slots.length?describeSlots(p.slots)+(p.complete?'':' · 部分时间未解析'):'上课时间待定';}
function teacherText(env,section){return env.esc(section.teachers.join('、')||'教师待定');}

function termsOf(env){
 const set=new Set();for(const id of Object.keys(env.details))for(const s of env.details[id].sections||[])if(s.term)set.add(s.term);
 return [...set].sort((a,b)=>b.localeCompare(a,'zh-CN'));
}

export function pickerView(env){
 const {esc}=env,p=st.prefs;
 if(!termsOf(env).includes(p.term))p.term=env.profile.term||p.term;
 const chosen=st.courseIds.map(id=>env.byId[id]).filter(Boolean);
 const parsed=st.parsed;
 const levelButtons=key=>[0,1,2].map(l=>`<button type="button" class="pk-level ${p[key]===l?'on':''} ${l===2?'must':''}" data-pk-level="${key}:${l}">${LEVELS[l]}</button>`).join('');
 const rows=CRITERIA.map(c=>{
  let extra='';
  if(c.key==='examWeight')extra=`<select class="pk-mini-select" data-pk-direction aria-label="考试占比方向">${Object.entries(c.options).map(([k,v])=>`<option value="${k}" ${p.examDirection===k?'selected':''}>${esc(v)}</option>`).join('')}</select>`;
  if(c.key==='freeDays')extra=`<span class="pk-days">${DAYS.map((d,i)=>`<button type="button" class="pk-day ${p.freeDayList.includes(i+1)?'on':''}" data-pk-day="${i+1}">${d}</button>`).join('')}</span>`;
  return `<div class="pk-row ${p[c.key]?'active':''}"><div class="pk-row-text"><strong>${esc(c.label)}</strong><small>${esc(c.hint)}</small>${extra}</div><div class="pk-levels" role="group" aria-label="${esc(c.label)}">${levelButtons(c.key)}</div></div>`;
 }).join('');
 const parsedBox=parsed?`<div class="pk-parsed">${parsed.courses.length?`<div><span class="tiny-label">已识别课程</span> ${parsed.courses.map(c=>`<span class="pill">${esc(c.name)} · ${esc(c.code)}</span>`).join(' ')}</div>`:''}${parsed.matchedRules.length?`<div><span class="tiny-label">已识别要求</span> ${parsed.matchedRules.map(r=>`<span class="pill gray">${esc(r)}</span>`).join(' ')}</div>`:''}${parsed.ambiguous.map(a=>`<div class="pk-ambiguous"><span>「${esc(a.query)}」是哪一门？</span>${a.options.map(o=>`<button type="button" class="choice" data-pk-add="${o.id}">${esc(o.name)}<small>${esc(o.code)} · ${esc(o.departments[0]||'')}</small></button>`).join('')}</div>`).join('')}${parsed.unmatched.length?`<div class="muted">没认出：${parsed.unmatched.map(esc).join('、')}——可以在下面按课名、代码或拼音首字母搜索。</div>`:''}</div>`:'';
 const search=st.query?searchResults(env):'';
 return env.hero('说出要求，<em>老师帮你挑好。</em>','写下想选的课和你在意的事：点不点名、考试占多少、有没有早八……课途逐个教学班比对官方考核表与课评摘要，排出时间不冲突的选老师方案。')
 +`<div class="pk-grid"><section class="panel"><div class="panel-head"><div><span class="eyebrow">STEP 1 · 一句话说需求</span><h3>想选什么课，在意什么</h3></div></div><div class="panel-body"><textarea id="pk-text" class="pk-text" rows="3" placeholder="例如：数理统计、大学物理B(下)，不点名，期末占比小，不要早八，周五空出来">${esc(st.text)}</textarea><div class="pk-actions"><button type="button" class="button primary" id="pk-parse">识别需求</button><span class="muted pk-tip">加“必须”就是硬条件，例如“必须不点名”。</span></div><div class="tags pk-examples">${EXAMPLES.map((e,i)=>`<button type="button" class="text-button" data-pk-example="${i}">试试：${esc(e)}</button>`).join('')}</div>${parsedBox}</div></section>`
 +`<section class="panel"><div class="panel-head"><div><span class="eyebrow">STEP 2 · 想选的课</span><h3>${chosen.length?`已选 ${chosen.length} 门`:'还没有课程'}</h3></div><select id="pk-term" aria-label="学期">${termsOf(env).map(t=>`<option ${t===p.term?'selected':''}>${esc(t)}</option>`).join('')}</select></div><div class="panel-body"><div class="tags pk-chosen">${chosen.map(c=>{const n=candidateSections(env.details[c.id],p).length;return `<span class="pk-chip">${esc(c.name)} <small>${esc(c.code)} · ${n} 个班</small><button type="button" aria-label="移除 ${esc(c.name)}" data-pk-remove="${c.id}">×</button></span>`;}).join('')||'<span class="muted">在上面一句话写出课名，或在这里搜索添加。</span>'}</div><div class="searchbar pk-search"><span>⌕</span><input id="pk-query" aria-label="搜索课程" placeholder="课程名 / 代码 / 拼音首字母" value="${esc(st.query)}"></div><div id="pk-results">${search}</div><label class="check-row"><input type="checkbox" id="pk-normal" ${p.normalOnly?'checked':''}> 只看普通班（不含荣誉课、英才班）</label><label class="check-row"><input type="checkbox" id="pk-avoid" ${p.avoidSelected?'checked':''}> 避开「我的课表」里其他课的时间（当前 ${env.selected.length} 门）</label></div></section></div>`
 +`<section class="panel pk-prefs"><div class="panel-head"><div><span class="eyebrow">STEP 3 · 要求</span><h3>每一项选“无所谓 / 尽量 / 必须”</h3></div><button type="button" class="button primary" id="pk-run">帮我挑老师 →</button></div><div class="panel-body pk-rows">${rows}</div><div class="panel-foot pk-foot muted">“必须”不满足的班直接排除，“尽量”只影响排序；没有数据的项目标为 ?，既不加分也不排除。课途不预测给分，也不估算拿 A 的概率。</div></section>`
 +resultView(env);
}

function searchResults(env){
 const {esc}=env,p=st.prefs;
 const hit=matchCourse(st.query,env.courses,{term:p.term,details:env.details});
 const list=hit.exact?[hit.exact]:hit.options;
 if(!list.length)return `<div class="muted pk-empty">${esc(p.term)} 没有找到「${esc(st.query)}」。</div>`;
 return `<div class="pk-search-list">${list.slice(0,8).map(c=>`<button type="button" class="choice" data-pk-add="${c.id}" ${st.courseIds.includes(c.id)?'disabled':''}>${esc(c.name)}<small>${esc(c.code)} · ${esc(c.teachers.slice(0,4).join('、'))}</small></button>`).join('')}</div>`;
}

function resultView(env){
 const r=st.result,{esc}=env;
 if(!r)return '';
 if(!r.rankings.length)return `<div class="empty">先添加至少一门想选的课。</div>`;
 const comboCards=r.combos.combos.map((c,i)=>{
  const items=c.items.map(x=>x.row?`<div class="pk-combo-row"><span class="pk-course">${esc(x.course.name)}</span><span><strong>${teacherText(env,x.row.section)}</strong> <small class="muted">${esc(x.row.section.code)}</small></span><span class="muted">${esc(timeText(x.row.section))}</span><span class="pk-badges">${x.row.checks.map(ch=>badge(env,ch)).join('')}</span></div>`:`<div class="pk-combo-row missing"><span class="pk-course">${esc(x.course.name)}</span><span>排不进：${esc(missingReason(r,x.course))}</span></div>`).join('');
  return `<article class="panel pk-combo"><div class="panel-head"><div><span class="eyebrow">方案 ${'一二三'[i]}</span><h3>${c.missing.length?`可排 ${c.items.length-c.missing.length} / ${c.items.length} 门`:`${c.items.length} 门全部排进`}<small class="muted"> · 匹配分 ${c.score}</small></h3></div><button type="button" class="button ${i===0?'primary':''}" data-pk-apply="${i}">放进我的课表（方案 ${esc(env.activeSlot)}）</button></div><div class="panel-body">${items}</div></article>`;
 }).join('');
 const empty=r.combos.emptyCourses.length?`<div class="notice">以下课程在当前条件下没有可选的班：${r.combos.emptyCourses.map(c=>esc(c.name)+'——'+esc(missingReason(r,c))).join('；')}。可以把相关“必须”改成“尽量”，或换个学期。</div>`:'';
 const ranking=r.rankings.map(g=>{
  const rows=g.rows.map((x,i)=>`<tr class="${x.blocked.length?'blocked':''}"><td>${i+1}</td><td><strong>${teacherText(env,x.section)}</strong><br><small class="muted">${esc(x.section.code)} · ${esc(x.section.class_type||'')}</small></td><td>${esc(timeText(x.section))}${x.section.capacity?`<br><small class="muted">往期 ${x.section.enrolled??'?'} / ${x.section.capacity} 人</small>`:''}</td><td class="pk-badges">${x.checks.map(ch=>badge(env,ch)).join('')||'<span class="muted">未设置要求</span>'}${x.blocked.length?`<div class="pk-blocked">不满足“必须”：${x.blocked.map(esc).join('、')}</div>`:''}</td><td>${x.evidence.length?`<details><summary>${x.evidence.length} 条课评摘要</summary>${x.evidence.map(e=>`<p><b>${esc(e.title)}</b><br>${esc(e.teaching)} ${esc(e.workload)} ${esc(e.assessment)}<br><small class="muted">${esc(e.source)}</small></p>`).join('')}</details>`:'<span class="muted">暂无课评摘要</span>'}</td><td><button type="button" class="button ghost" data-pk-pick="${g.course.id}:${x.section.id}">选这个班</button></td></tr>`).join('');
  return `<details class="panel pk-rank" ${r.rankings.length<=2?'open':''}><summary class="panel-head"><div><span class="eyebrow">${esc(g.course.code)} · ${g.rows.length} 个班</span><h3>${esc(g.course.name)} 的老师排序</h3></div><span class="pk-toggle muted">展开 / 收起</span></summary><div class="pk-rank-tools"><button type="button" class="text-button" data-course="${g.course.id}">查看这门课的全部证据 ↗</button></div><div class="table-scroll"><table class="pk-table"><thead><tr><th>#</th><th>教师 / 班号</th><th>时间</th><th>符合情况</th><th>课评</th><th></th></tr></thead><tbody>${rows||'<tr><td colspan="6" class="muted">该学期没有开课班次。</td></tr>'}</tbody></table></div></details>`;
 }).join('');
 return `<div class="section-title pk-result-title"><h2>推荐组合</h2><span class="muted">按要求打分后，挑出时间互不冲突、总分最高的 ${r.combos.combos.length} 套</span></div>${empty}${comboCards||'<div class="empty">没有找到能同时排进的组合。</div>'}<div class="section-title pk-result-title"><h2>逐门课的老师排序</h2><span class="muted">✓ 符合　✗ 不符合　≈ 说法不一　? 无数据；鼠标停在标签上看依据</span></div>${ranking}<p class="muted pk-disclaimer">依据：教务系统教学班考核表与考试形式（${esc(st.prefs.term)}），以及站内按教师整理的往期课评摘要。考核和点名习惯可能逐学期变化，请以开课后老师的说明为准。</p>`;
}

function missingReason(r,course){
 const g=r.rankings.find(x=>x.course.id===course.id);
 if(!g||!g.rows.length)return '这个学期没有可选的班';
 const open=g.rows.filter(x=>!x.blocked.length);
 if(open.length)return `${open.length} 个满足条件的班都和其他课时间冲突`;
 const why={};
 for(const x of g.rows)for(const label of x.blocked){const c=x.checks.find(ch=>ch.label===label);why[label]||=c?.detail||'';}
 return `${g.rows.length} 个班都不满足“必须”：`+Object.entries(why).map(([k,v])=>v?`${k}（如 ${v}）`:k).join('；');
}

function run(env){
 const p=st.prefs;
 const courses=st.courseIds.map(id=>env.byId[id]).filter(Boolean);
 const rankings=courses.map(c=>({course:c,rows:rankTeachers(c,env.details[c.id],p)}));
 const fixed=p.avoidSelected?env.selected.filter(i=>!st.courseIds.includes(i.course.id)):[];
 st.result={rankings,combos:bestCombos(rankings,{fixed})};
}

export function bindPicker(env){
 const $=s=>document.querySelector(s),rerender=()=>{save();env.rerender();};
 const text=$('#pk-text');if(!text)return;
 text.oninput=()=>{st.text=text.value;save();};
 $('#pk-parse').onclick=()=>{
  st.text=text.value;
  const parsed=parseRequest(st.text,env.courses,{term:st.prefs.term,details:env.details,plan:env.profile.plan});
  const keep={normalOnly:st.prefs.normalOnly,avoidSelected:st.prefs.avoidSelected};
  st.prefs={...parsed.prefs,...keep};
  for(const c of parsed.courses)if(!st.courseIds.includes(c.id))st.courseIds.push(c.id);
  st.parsed=parsed;st.result=null;rerender();
 };
 document.querySelectorAll('[data-pk-example]').forEach(b=>b.onclick=()=>{st.text=EXAMPLES[Number(b.dataset.pkExample)];rerender();});
 document.querySelectorAll('[data-pk-level]').forEach(b=>b.onclick=()=>{const [k,l]=b.dataset.pkLevel.split(':');st.prefs[k]=Number(l);if(k==='freeDays'&&Number(l)&&!st.prefs.freeDayList.length)env.toast('再点一下要空出的星期');st.result=null;rerender();});
 document.querySelectorAll('[data-pk-day]').forEach(b=>b.onclick=()=>{const d=Number(b.dataset.pkDay),list=st.prefs.freeDayList;st.prefs.freeDayList=list.includes(d)?list.filter(x=>x!==d):[...list,d].sort();if(st.prefs.freeDayList.length&&!st.prefs.freeDays)st.prefs.freeDays=1;st.result=null;rerender();});
 const dir=document.querySelector('[data-pk-direction]');if(dir)dir.onchange=()=>{st.prefs.examDirection=dir.value==='high'?'high':'low';if(!st.prefs.examWeight)st.prefs.examWeight=1;st.result=null;rerender();};
 $('#pk-term').onchange=e=>{st.prefs.term=e.target.value;st.result=null;rerender();};
 $('#pk-normal').onchange=e=>{st.prefs.normalOnly=e.target.checked;st.result=null;rerender();};
 $('#pk-avoid').onchange=e=>{st.prefs.avoidSelected=e.target.checked;st.result=null;rerender();};
 const q=$('#pk-query');
 q.oninput=()=>{st.query=q.value;const box=$('#pk-results');box.innerHTML=st.query.trim()?searchResults(env):'';bindAdd(env,rerender);};
 bindAdd(env,rerender);
 document.querySelectorAll('[data-pk-remove]').forEach(b=>b.onclick=()=>{st.courseIds=st.courseIds.filter(id=>id!==b.dataset.pkRemove);st.result=null;rerender();});
 $('#pk-run').onclick=()=>{
  if(!st.courseIds.length){env.toast('先添加至少一门想选的课');return;}
  if(st.prefs.freeDays&&!st.prefs.freeDayList.length){env.toast('“空出某几天”还没选星期');return;}
  run(env);rerender();
  setTimeout(()=>document.querySelector('.pk-result-title')?.scrollIntoView({behavior:'smooth',block:'start'}),30);
 };
 document.querySelectorAll('[data-pk-apply]').forEach(b=>b.onclick=()=>{
  const combo=st.result?.combos.combos[Number(b.dataset.pkApply)];if(!combo)return;
  const items=combo.items.filter(x=>x.row).map(x=>({course:x.course,section:x.row.section,reason:'按要求挑老师'}));
  env.addItems(items);
  const clash=conflicts(env.selected).length;
  env.toast(`已放进方案 ${env.activeSlot}：${items.length} 门课`+(clash?`；课表里还有 ${clash} 组冲突，请到“我的课表”查看`:''));
 });
 document.querySelectorAll('[data-pk-pick]').forEach(b=>b.onclick=()=>{const [cid,sid]=b.dataset.pkPick.split(':');const course=env.byId[cid],section=env.details[cid]?.sections.find(s=>s.id===sid);if(!course||!section)return;env.addItems([{course,section,reason:'按要求挑老师'}]);env.toast(`已加入 ${course.name} · ${section.teachers.join('、')}`);});
}

function bindAdd(env,rerender){
 document.querySelectorAll('[data-pk-add]').forEach(b=>b.onclick=()=>{const id=b.dataset.pkAdd;if(!st.courseIds.includes(id)){if(st.courseIds.length>=12){env.toast('一次最多比较 12 门课');return;}st.courseIds.push(id);}if(st.parsed)st.parsed.ambiguous=st.parsed.ambiguous.filter(a=>!a.options.some(o=>o.id===id));st.query='';st.result=null;rerender();});
}

// 测试用：重置页面状态
export function _resetPickerState(){st={text:'',courseIds:[],prefs:defaultPrefs(),parsed:null,result:null,query:''};}
