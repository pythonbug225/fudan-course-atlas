// 课途 · 按要求挑老师
// 依据：教学班官方考核占比、考试形式、上课时间，以及按教师整理的课评摘要。
// 不预测给分或拿 A 概率；缺数据的条件按“无数据”处理，不算符合也不算不符合。
import {parseSchedule,overlap,searchCourses} from './engine.js';

export const LEVELS={0:'无所谓',1:'尽量',2:'必须'};
export const DAYS=['一','二','三','四','五','六','日'];

// key → 展示名称；kind 决定取值方式
export const CRITERIA=[
 {key:'noRollcall',label:'不点名 / 出勤分低',hint:'官方出勤占比 + 课评里的点名、签到描述'},
 {key:'examWeight',label:'考试占比',hint:'期中＋期末合计占总评的比例',options:{low:'小（平时分为主）',high:'大（一考定音）'}},
 {key:'noMidterm',label:'没有期中考试',hint:'官方考核表里期中占比为 0'},
 {key:'openBook',label:'开卷或不考试',hint:'考试形式：开卷、半开卷、论文、无期末'},
 {key:'noPresentation',label:'不用 pre / 汇报',hint:'官方汇报、研讨占比 + 课评里的 pre、展示'},
 {key:'noPaper',label:'不写论文',hint:'官方课题论文占比、考试形式为论文'},
 {key:'lightHomework',label:'作业分占比小',hint:'作业、实验、实践类占比'},
 {key:'noEarly',label:'不要早八',hint:'不排第 1–2 节'},
 {key:'noEvening',label:'不要晚课',hint:'不排第 11 节及以后'},
 {key:'freeDays',label:'空出某几天',hint:'这些天不排课'},
 {key:'hasReviews',label:'有学生课评的老师',hint:'有课评摘要的老师优先'},
];

export const defaultPrefs=()=>({term:'2026春',normalOnly:true,avoidSelected:true,noRollcall:0,examWeight:0,examDirection:'low',noMidterm:0,openBook:0,noPresentation:0,noPaper:0,lightHomework:0,noEarly:0,noEvening:0,freeDays:0,freeDayList:[],hasReviews:0});

export function cleanPrefs(value={}){
 const base=defaultPrefs(),p=value&&typeof value==='object'?value:{};
 const out={...base};
 for(const c of CRITERIA)out[c.key]=[0,1,2].includes(Number(p[c.key]))?Number(p[c.key]):0;
 out.term=typeof p.term==='string'&&/^20\d{2}(春|秋|暑)$/.test(p.term)?p.term:base.term;
 out.examDirection=p.examDirection==='high'?'high':'low';
 out.normalOnly=p.normalOnly!==false;
 out.avoidSelected=p.avoidSelected!==false;
 out.freeDayList=Array.isArray(p.freeDayList)?[...new Set(p.freeDayList.map(Number).filter(d=>d>=1&&d<=7))].sort():[];
 return out;
}

const clamp=(x,lo=-1,hi=1)=>Math.max(lo,Math.min(hi,x));
const pct=n=>Math.round(n*10)/10;

// ── 考核表 → 各类占比 ──────────────────────────────────────────
export function assessmentShares(section){
 const rows=Array.isArray(section.assessment)?section.assessment:[];
 if(!rows.length)return null;
 const s={final:0,midterm:0,attendance:0,homework:0,presentation:0,paper:0,participation:0,other:0,total:0};
 for(const r of rows){
  const v=Number(r.percentage)||0,c=String(r.criteria||'');s.total+=v;
  if(/^期末/.test(c))s.final+=v;
  else if(/^期中/.test(c))s.midterm+=v;
  else if(/^出勤|考勤|签到/.test(c))s.attendance+=v;
  else if(/^(作业|实验|实践|单元学习|线上学习)/.test(c))s.homework+=v;
  else if(/^(汇报|课题研讨|分组讨论|展示)/.test(c))s.presentation+=v;
  else if(/^课题论文|论文/.test(c))s.paper+=v;
  else if(/^课堂表现/.test(c))s.participation+=v;
  else s.other+=v;
 }
 return s.total>0?s:null;
}

// ── 课评摘要 → 点名 / pre 倾向 ─────────────────────────────────
const LOW_ROLL=/(不点名|无常规点名|不正式点名|少点名|很少点名|几乎不点名|从不点名|无常规考勤|少考勤|不考勤|无常规签到|不签到|无考勤|少签到|少量签到|偶尔点名|偶尔签到|偶有考勤|点名不直接扣分)/g;
const HIGH_ROLL=/(每节(课)?点名|基本每课点名|每课点名|每次(课)?点名|经常点名|多次点名|随机点名|定位签到|二维码签到|每课(线上)?签到|全班点名|请假手续严格)/g;
const SOME_ROLL=/(签到|点名|考勤)/g;
const NO_PRE=/(无\s?pre|不\s?pre|没有\s?pre|无展示|不用展示|无汇报|不需要?展示)/gi;
const PRE=/(pre|展示|汇报|presentation)/gi;

function evidenceText(e){return [e.teaching,e.workload,e.assessment].filter(Boolean).join(' ');}
export function evidenceFor(courseDetail,section){
 const ev=courseDetail?.evidence||[];
 return ev.filter(e=>section.teachers.includes(e.teacher));
}
function snippet(text,re){
 re.lastIndex=0;const m=re.exec(text);if(!m)return '';
 const start=Math.max(0,m.index-14),end=Math.min(text.length,m.index+m[0].length+18);
 return (start>0?'…':'')+text.slice(start,end).trim()+(end<text.length?'…':'');
}
export function rollcallSignal(evidence){
 let low=0,high=0,some=0,quoteLow='',quoteHigh='',quoteSome='';
 for(const e of evidence){
  const t=evidenceText(e);
  const lows=t.match(LOW_ROLL)||[];
  const stripped=t.replace(LOW_ROLL,'');
  const highs=stripped.match(HIGH_ROLL)||[];
  const somes=stripped.replace(HIGH_ROLL,'').match(SOME_ROLL)||[];
  if(lows.length){low+=lows.length;quoteLow||=snippet(t,LOW_ROLL);}
  if(highs.length){high+=highs.length;quoteHigh||=snippet(stripped,HIGH_ROLL);}
  else if(somes.length){some+=somes.length;quoteSome||=snippet(stripped,SOME_ROLL);}
 }
 if(!low&&!high&&!some)return null;
 if(low&&!high&&!some)return {value:'low',quote:quoteLow};
 if(high&&!low)return {value:'high',quote:quoteHigh};
 if(some&&!low&&!high)return {value:'some',quote:quoteSome};
 return {value:'mixed',quote:[quoteLow,quoteHigh||quoteSome].filter(Boolean).join(' / ')};
}
export function presentationSignal(evidence){
 let no=0,yes=0,q='';
 for(const e of evidence){
  const t=evidenceText(e);
  const n=t.match(NO_PRE)||[];const rest=t.replace(NO_PRE,'');const y=rest.match(PRE)||[];
  if(n.length){no++;q||=snippet(t,NO_PRE);}
  if(y.length){yes++;q||=snippet(rest,PRE);}
 }
 if(!no&&!yes)return null;
 return {value:no&&!yes?'none':yes&&!no?'has':'mixed',quote:q};
}

// ── 单个教学班打分 ────────────────────────────────────────────
// 每项结果：{key,label,status:'good'|'bad'|'mixed'|'unknown',score:-1..1,detail,source}
export function judgeSection(course,courseDetail,section,prefs){
 const p=cleanPrefs(prefs),shares=assessmentShares(section),ev=evidenceFor(courseDetail,section);
 const parsed=parseSchedule(section.schedule||'');
 const exam=String(section.exam||'');
 const checks=[];
 const add=(key,label,score,detail,source)=>{
  const status=score===null?'unknown':score>=0.25?'good':score<=-0.25?'bad':'mixed';
  checks.push({key,label,score,status,detail,source});
 };

 if(p.noRollcall){
  const sig=rollcallSignal(ev);
  const off=shares?(shares.attendance===0?0.4:shares.attendance<=5?0.15:shares.attendance<=10?-0.2:-0.6):null;
  const evScore=sig?{low:0.9,high:-0.9,some:-0.45,mixed:0}[sig.value]:null;
  const score=evScore===null&&off===null?null:evScore===null?off:off===null?evScore:clamp(evScore*0.75+off*0.25);
  const parts=[];
  if(shares)parts.push(`官方出勤 ${pct(shares.attendance)}%`);
  if(sig)parts.push(`课评：${sig.quote}`);
  add('noRollcall','不点名',score,parts.join('；')||'没有考核表和点名相关课评',sig?'课评摘要':'官方考核');
 }
 if(p.examWeight){
  if(!shares)add('examWeight','考试占比',null,'没有考核表','官方考核');
  else{
   const t=shares.final+shares.midterm;
   const score=p.examDirection==='low'?clamp((50-t)/40):clamp((t-50)/30);
   add('examWeight',p.examDirection==='low'?'考试占比小':'考试占比大',score,`期中 ${pct(shares.midterm)}% ＋ 期末 ${pct(shares.final)}% ＝ ${pct(t)}%`,'官方考核');
  }
 }
 if(p.noMidterm){
  if(!shares)add('noMidterm','没有期中',null,'没有考核表','官方考核');
  else add('noMidterm','没有期中',shares.midterm>0?-1:0.6,shares.midterm>0?`期中 ${pct(shares.midterm)}%`:'考核表无期中','官方考核');
 }
 if(p.openBook){
  let score=null,detail='考试形式未注明';
  if(/开卷|论文/.test(exam)&&!/闭卷/.test(exam)){score=exam.includes('半开卷')?0.5:1;detail='考试形式：'+exam;}
  else if(/闭卷|口试/.test(exam)){score=-1;detail='考试形式：'+exam;}
  else if(shares&&shares.final===0&&shares.midterm===0){score=0.8;detail='考核表没有期中、期末考试';}
  else if(ev.some(e=>/开卷/.test(evidenceText(e)))){score=0.5;detail='课评提到开卷';}
  else if(exam)detail='考试形式：'+exam;
  add('openBook','开卷 / 不考试',score,detail,'官方考核');
 }
 if(p.noPresentation){
  const sig=presentationSignal(ev);
  const off=shares?(shares.presentation>0?-clamp(shares.presentation/20,0.3,1):0.3):null;
  const evScore=sig?{none:0.8,has:-0.7,mixed:-0.2}[sig.value]:null;
  const score=off===null&&evScore===null?null:off===null?evScore:evScore===null?off:clamp(Math.min(off,evScore)*0.6+Math.max(off,evScore)*0.4);
  const parts=[];if(shares)parts.push(`官方汇报/研讨 ${pct(shares.presentation)}%`);if(sig)parts.push('课评：'+sig.quote);
  add('noPresentation','不用 pre',score,parts.join('；')||'没有相关数据',sig?'课评摘要':'官方考核');
 }
 if(p.noPaper){
  const paperExam=exam.includes('论文');
  const score=paperExam?-1:shares?(shares.paper>0?-clamp(shares.paper/20,0.3,1):0.4):null;
  add('noPaper','不写论文',score,paperExam?'考试形式：论文':shares?`官方课题论文 ${pct(shares.paper)}%`:'没有考核表','官方考核');
 }
 if(p.lightHomework){
  if(!shares)add('lightHomework','作业分少',null,'没有考核表','官方考核');
  else add('lightHomework','作业分少',clamp((25-shares.homework)/25),`作业/实验/实践 ${pct(shares.homework)}%`,'官方考核');
 }
 const timeKnown=parsed.slots.length>0;
 if(p.noEarly){
  const hit=parsed.slots.filter(s=>s.start<=2);
  add('noEarly','不要早八',timeKnown?(hit.length?-1:0.4):null,timeKnown?(hit.length?'有第 1–2 节：'+describeSlots(hit):'没有第 1–2 节'):'上课时间未解析','教务课表');
 }
 if(p.noEvening){
  const hit=parsed.slots.filter(s=>s.end>=11);
  add('noEvening','不要晚课',timeKnown?(hit.length?-1:0.3):null,timeKnown?(hit.length?'有晚课：'+describeSlots(hit):'没有晚课'):'上课时间未解析','教务课表');
 }
 if(p.freeDays&&p.freeDayList.length){
  const hit=parsed.slots.filter(s=>p.freeDayList.includes(s.day));
  add('freeDays','空出周'+p.freeDayList.map(d=>DAYS[d-1]).join('、'),timeKnown?(hit.length?-1:0.4):null,timeKnown?(hit.length?'占用：'+describeSlots(hit):'这些天没课'):'上课时间未解析','教务课表');
 }
 if(p.hasReviews){
  add('hasReviews','有课评',ev.length?0.6:-0.3,ev.length?`${ev.length} 条按教师整理的课评摘要`:'暂无该教师的课评摘要','课评摘要');
 }

 let score=0,blocked=[];
 for(const c of checks){
  const level=p[c.key];const w=level===2?3:1;
  if(c.score!==null)score+=w*c.score;
  if(level===2&&c.status==='bad')blocked.push(c.label);
 }
 return {course,section,evidence:ev,shares,checks,score:Math.round(score*100)/100,blocked,timeKnown:parsed.complete};
}

export function describeSlots(slots){
 return [...new Set(slots.map(s=>`周${DAYS[s.day-1]} ${s.start}${s.end>s.start?'–'+s.end:''}节`))].join('、');
}

export function candidateSections(courseDetail,prefs){
 const p=cleanPrefs(prefs);
 return (courseDetail?.sections||[]).filter(s=>s.term===p.term&&(!p.normalOnly||!/英才|荣誉/.test(s.class_type||'')));
}

export function rankTeachers(course,courseDetail,prefs){
 const rows=candidateSections(courseDetail,prefs).map(s=>judgeSection(course,courseDetail,s,prefs));
 return rows.sort((a,b)=>(a.blocked.length?1:0)-(b.blocked.length?1:0)||b.score-a.score||Number(b.timeKnown)-Number(a.timeKnown)||(b.evidence.length-a.evidence.length)||a.section.code.localeCompare(b.section.code));
}

// ── 组合：每门课选一个班，时间不冲突、总分最高 ──────────────────────
function slotsOf(section){return parseSchedule(section.schedule||'').slots;}
function clash(a,b){return a.some(x=>b.some(y=>overlap(x,y)));}

export function bestCombos(rankings,{fixed=[],limit=3,maxNodes=200000}={}){
 // rankings: [{course, rows:[judgeSection 结果]}]；fixed: 已在课表、需要避开的 {course,section}
 const fixedSlots=fixed.map(i=>slotsOf(i.section));
 const groups=rankings.map(r=>({course:r.course,rows:r.rows.filter(x=>!x.blocked.length).map(x=>({...x,slots:slotsOf(x.section)})).filter(x=>!fixedSlots.some(f=>clash(f,x.slots)))}));
 const order=groups.map((g,i)=>i).sort((a,b)=>groups[a].rows.length-groups[b].rows.length);
 const SKIP=-1000; // 第二轮：某门课实在排不进时允许空着，但大幅扣分
 let nodes=0;
 function search(allowSkip){
  const best=[],pick=new Array(groups.length).fill(null);
  const top=i=>{const m=groups[i].rows.length?Math.max(...groups[i].rows.map(r=>r.score)):-Infinity;return allowSkip?Math.max(SKIP,m):m;};
  const maxRest=order.map((_,k)=>order.slice(k).reduce((a,i)=>a+top(i),0));
  const record=score=>{
   const items=pick.map((r,i)=>({course:groups[i].course,row:r}));
   const key=items.map(x=>x.row?.section.id||'-').join('|');
   if(best.some(b=>b.key===key))return;
   best.push({key,score:Math.round(score*100)/100,items,missing:items.filter(x=>!x.row).map(x=>x.course)});
   best.sort((a,b)=>b.score-a.score);if(best.length>limit)best.pop();
  };
  const walk=(k,score,taken)=>{
   if(++nodes>maxNodes)return;
   if(k===order.length){record(score);return;}
   if(best.length>=limit&&score+maxRest[k]<=best[best.length-1].score)return;
   const gi=order[k];
   for(const r of groups[gi].rows){
    if(taken.some(t=>clash(t,r.slots)))continue;
    pick[gi]=r;walk(k+1,score+r.score,[...taken,r.slots]);pick[gi]=null;
   }
   if(allowSkip)walk(k+1,score+SKIP,taken);
  };
  walk(0,0,fixedSlots);
  return best;
 }
 let combos=groups.some(g=>!g.rows.length)?[]:search(false);
 if(!combos.length&&groups.length)combos=search(true).map(c=>({...c,score:Math.round((c.score-SKIP*c.missing.length)*100)/100}));
 return {combos,nodes,truncated:nodes>maxNodes,emptyCourses:groups.filter(g=>!g.rows.length).map(g=>g.course)};
}

// ── 一句话需求解析 ────────────────────────────────────────────
const RULES=[
 [/(不|别|不要|不想|讨厌|拒绝)(被)?(点名|签到|考勤)|不点名|免点名|不查考勤/, p=>p.noRollcall=Math.max(p.noRollcall,1)],
 [/(期中)?(期末|考试)(的)?(占比|比重|权重|比例)?\s*(小|低|少|轻)|平时分(占比)?(高|大|多)|少考试/, p=>{p.examWeight=Math.max(p.examWeight,1);p.examDirection='low';}],
 [/(期中)?(期末|考试)(的)?(占比|比重|权重|比例)?\s*(大|高|多|重)|一考定|平时分(占比)?(低|小|少)/, p=>{p.examWeight=Math.max(p.examWeight,1);p.examDirection='high';}],
 [/(不要|没有|无|别有|不想要?)期中/, p=>p.noMidterm=Math.max(p.noMidterm,1)],
 [/开卷|不考试|不用考试|无考试/, p=>p.openBook=Math.max(p.openBook,1)],
 [/(不要|不想|不用|没有|无|别)\s?(pre|PRE|Pre|展示|汇报|presentation)/, p=>p.noPresentation=Math.max(p.noPresentation,1)],
 [/(不要|不想|不用|不写|没有|无|别)(写)?论文/, p=>p.noPaper=Math.max(p.noPaper,1)],
 [/作业(少|轻|不多)|(不要|少)作业/, p=>p.lightHomework=Math.max(p.lightHomework,1)],
 [/(不要|不想|没有|无|别|拒绝)\s?(上)?(早八|早课)|不早起|1-2节|一二节/, p=>p.noEarly=Math.max(p.noEarly,1)],
 [/(不要|不想|没有|无|别|拒绝)\s?(上)?(晚课|晚上的课)/, p=>p.noEvening=Math.max(p.noEvening,1)],
 [/有(学生)?课评|口碑|有评价/, p=>p.hasReviews=Math.max(p.hasReviews,1)],
];
const MUST=/(必须|一定|绝对|千万|坚决)/;
const DAY_RE=/(周|星期|礼拜)([一二三四五六日天])/g;

export function parseRequest(text,courses,{term,details,plan}={}){
 const prefs=defaultPrefs();if(term)prefs.term=term;
 const clauses=String(text||'').split(/[，,。；;\n]+/).map(s=>s.trim()).filter(Boolean);
 const leftover=[],matchedRules=[];
 for(const clause of clauses){
  let used=false;
  for(const [re,apply] of RULES){
   if(re.test(clause)){
    const before={...prefs};apply(prefs);used=true;
    if(MUST.test(clause))for(const k of Object.keys(prefs))if(typeof prefs[k]==='number'&&prefs[k]!==before[k]&&prefs[k]===1)prefs[k]=2;
    matchedRules.push(clause);
   }
  }
  if(/(空|没课|不上课|休息|空出)/.test(clause)&&DAY_RE.test(clause)){
   DAY_RE.lastIndex=0;let m;while((m=DAY_RE.exec(clause)))prefs.freeDayList.push('一二三四五六日'.indexOf(m[2]==='天'?'日':m[2])+1);
   prefs.freeDays=MUST.test(clause)?2:Math.max(prefs.freeDays,1);used=true;matchedRules.push(clause);
  }
  DAY_RE.lastIndex=0;
  if(/秋/.test(clause)&&/20\d{2}/.test(clause)){const y=clause.match(/20\d{2}/)[0];prefs.term=y+'秋';used=true;}
  else if(/春/.test(clause)&&/20\d{2}/.test(clause)){const y=clause.match(/20\d{2}/)[0];prefs.term=y+'春';used=true;}
  if(!used)leftover.push(clause);
 }
 prefs.freeDayList=[...new Set(prefs.freeDayList)].sort();
 const found=[],ambiguous=[],unmatched=[];
 for(const piece of leftover.flatMap(s=>s.split(/[、和跟及与\s]+|还有|以及|我想选|想选|要选|选/)).map(s=>s.replace(/^(我想|想|要|上|修)/,'').trim()).filter(s=>s.length>=2)){
  const hit=matchCourse(piece,courses,{term:prefs.term,details,plan});
  if(hit.exact)found.push(hit.exact);
  else if(hit.options.length)ambiguous.push({query:piece,options:hit.options});
  else unmatched.push(piece);
 }
 return {prefs:cleanPrefs(prefs),courses:[...new Map(found.map(c=>[c.id,c])).values()],ambiguous,unmatched,matchedRules};
}

export function matchCourse(query,courses,{term,details,plan}={}){
 const q=query.trim(),lower=q.toLowerCase();
 const offered=c=>!term||!details||(details[c.id]?.sections||[]).some(s=>s.term===term);
 const pool=courses.filter(offered);
 const exact=pool.filter(c=>c.name===q||c.code.toLowerCase()===lower);
 if(exact.length===1)return {exact:exact[0],options:[]};
 // 同名课不止一门时，只有一门在本人培养方案里就直接选它
 const inPlan=plan?exact.filter(c=>(c.plans||[]).some(x=>String(x.id)===String(plan))):[];
 if(inPlan.length===1)return {exact:inPlan[0],options:[]};
 const norm=s=>s.replace(/[（(].*?[)）]/g,'').replace(/\s+/g,'');
 const loose=pool.filter(c=>norm(c.name)===norm(q));
 if(loose.length===1)return {exact:loose[0],options:[]};
 const hits=exact.length?exact:loose.length?loose:searchCourses(pool,q);
 const sorted=hits.sort((a,b)=>Number(b.name.startsWith(q))-Number(a.name.startsWith(q))||a.name.length-b.name.length||a.code.localeCompare(b.code));
 if(sorted.length===1)return {exact:sorted[0],options:[]};
 return {exact:null,options:sorted.slice(0,8)};
}
