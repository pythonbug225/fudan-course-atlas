export const GOALS={research:{label:'数学 × AI 科研',words:['数理统计','数学模型','离散数学','微分方程数值解法','概率论','人工智能导论','程序设计实践'],outcome:'把数学基础连接到可复现的 AI 研究项目'},industry:{label:'数据与工程实践',words:['数据结构','程序设计','数据库','人工智能导论','软件','数理统计','数学模型'],outcome:'建立算法、编程与数据分析的项目组合'},explore:{label:'跨学科探索',words:['文学','哲学','社会','心理','历史','人工智能','科学'],outcome:'用一组课程试探兴趣，并保留转向空间'},balanced:{label:'扎实基础 · 均衡投入',words:['数学模型','数理统计','离散数学','概率论','英语','美学','文学'],outcome:'在专业推进、兴趣拓展和学期节奏之间取得平衡'}};
export function parseSchedule(text=''){
 const slots=[],unknown=[];
 for(const line of text.split(/[;；\n]+/).map(s=>s.trim()).filter(Boolean)){
  const m=line.match(/^(.+?)周\s*星期([一二三四五六日天])\s*(\d+)(?:\s*[~～\-–]\s*(\d+))?节/);
  if(!m){unknown.push(line);continue;}
  let weeks=[];let valid=true;
  for(const token of m[1].split(/[,，、]/)){
   const w=token.trim().match(/^(\d+)(?:[~～\-–](\d+))?(?:[（(](单|双)[）)])?$/);
   if(!w){valid=false;break;}
   const from=Number(w[1]),to=Number(w[2]||w[1]);if(from>to||to>30){valid=false;break;}
   for(let n=from;n<=to;n++)if(!w[3]||(w[3]==='单'?n%2:!(n%2)))weeks.push(n);
  }
  const start=Number(m[3]),end=Number(m[4]||m[3]);
  if(!valid||end<start||end>20){unknown.push(line);continue;}
  const day='一二三四五六日'.indexOf(m[2]==='天'?'日':m[2])+1;
  const item={day,start,end,weeks:[...new Set(weeks)],location:line.slice(m[0].length).trim().split(/\s+/)[0]||'',raw:line};
  if(!slots.some(s=>JSON.stringify(s)===JSON.stringify(item)))slots.push(item);
 }
 return {slots,unknown,complete:slots.length>0&&unknown.length===0};
}
export function overlap(a,b){return a.day===b.day&&a.start<=b.end&&b.start<=a.end&&a.weeks.some(w=>b.weeks.includes(w));}
export function conflicts(items){
 const pairs=[];for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){
  const a=parseSchedule(items[i].section.schedule),b=parseSchedule(items[j].section.schedule);
  if(a.slots.some(x=>b.slots.some(y=>overlap(x,y))))pairs.push([items[i],items[j]]);
 }return pairs;
}
export function creditTotal(items){return Math.round(items.reduce((a,i)=>a+Number(i.section.credits||0),0)*10)/10;}
export function searchCourses(courses,q){const tokens=q.toLowerCase().trim().split(/\s+/).filter(Boolean);return courses.filter(c=>{const str=[c.name,c.code,...c.teachers,...(c.aliases||[])].join(' ').toLowerCase();return tokens.every(t=>str.includes(t));});}
export function rankCourses(courses,details,p){
 const goal=GOALS[p.goal]||GOALS.research;
 return courses.filter(c=>!p.completed.some(n=>n===c.code||n===c.name)).map(c=>{
  const sections=(details[c.id]?.sections||[]).filter(s=>s.term===p.term);
  const goalMatch=goal.words.findIndex(w=>c.name.includes(w));
  const planMatch=c.plans.some(x=>String(x.id)===String(p.plan));
  const general=c.code.startsWith('GE');
  const score=(goalMatch>=0?65-goalMatch*3:0)+(planMatch?30:0)+(general?12:0)+(c.has_reviews?4:0);
  const eligible=planMatch||general||!p.plan;
  return {course:c,sections,score,eligible,reason:goalMatch>=0?'衔接'+goal.label:planMatch?'关联所选专业培养方案':'公共通识拓展'};
 }).filter(x=>x.eligible&&x.sections.length&&x.score>8).sort((a,b)=>b.score-a.score||a.course.code.localeCompare(b.course.code));
}
export function buildPlan(courses,details,p,locked=[]){
 const ranked=rankCourses(courses,details,p),items=[...locked],log=[];let skipped=0;
 for(const r of ranked){
  if(items.some(x=>x.course.id===r.course.id))continue;
  const opts=[...r.sections].sort((a,b)=>Number(parseSchedule(b.schedule).complete)-Number(parseSchedule(a.schedule).complete));
  const section=opts.find(s=>{
   if(creditTotal(items)+Number(s.credits||0)>Number(p.maxCredits))return false;
   if(p.foreignCodes?.includes(r.course.code)&&creditTotal(items.filter(i=>p.foreignCodes.includes(i.course.code)))+Number(s.credits||0)>p.foreignCreditCap)return false;
   const parsed=parseSchedule(s.schedule);
   if(p.freeWednesday&&parsed.slots.some(t=>t.day===3&&t.end>=6&&t.start<=10))return false;
   return !conflicts([...items,{course:r.course,section:s}]).length;
  });
  if(section)items.push({course:r.course,section,reason:r.reason});else skipped++;
  if(creditTotal(items)>=Math.max(1,p.maxCredits-1))break;
 }
 log.push({tool:'课程检索',result:`检索 ${courses.length.toLocaleString()} 张课程卡，找到 ${ranked.length} 个目标学期候选`});
 log.push({tool:'班次与时间校验',result:`逐班检查周次、星期和节次；跳过 ${skipped} 个当前约束下的候选`});
 log.push({tool:'学分汇总',result:`生成 ${items.length} 门课程、${creditTotal(items)} 学分的候选组合`});
 const unknown=items.filter(i=>!parseSchedule(i.section.schedule).complete).length;
 log.push({tool:'时间信息覆盖',result:unknown?`${unknown} 门课程待补上课时间`:'所选课程的周次与节次均已解析'});
 return {items,log,unknown,conflicts:conflicts(items)};
}
