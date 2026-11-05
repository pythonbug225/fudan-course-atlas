// Deterministic curriculum accounting. Parent totals roll up unique records.
export const norm = v => String(v || '').trim().toUpperCase();
const n = v => Number(v) || 0;
const sum = xs => Math.round(xs.reduce((a,b)=>a+n(b),0)*100)/100;
export function composeCurriculum(publicPlan, major, profile={}) {
  const nodes=structuredClone(major.modules).map(m=>({...m,id:'major:'+m.id,parent:m.parent?'major:'+m.parent:null,source:major.title,origin:'major'}));
  const pub=new Map(publicPlan.modules.map(m=>[m.id,m]));
  const refs=new Map(nodes.filter(m=>m.referenceId).map(m=>[m.referenceId,m.id]));
  const existing=new Map(nodes.map(m=>[m.id,m]));
  function expand(rawId,parent,trail=new Set()) {
    if(trail.has(rawId))return;trail=new Set([...trail,rawId]);
    const raw=pub.get(rawId); if(!raw)return;
    let id=refs.get(rawId)||'public:'+rawId;
    let node=existing.get(id);
    if(!node){node={...structuredClone(raw),id,parent,source:publicPlan.title,origin:'public'};nodes.push(node);existing.set(id,node);}
    if(!node.courses.length)node.courses=structuredClone(raw.courses);
    node.publicNote=raw.note;
    for(const child of publicPlan.modules.filter(m=>m.parent===rawId))expand(child.id,id,trail);
  }
  for(const node of [...nodes])if(node.referenceId)expand(node.referenceId,node.parent);
  if(!refs.size){const base=publicPlan.modules.find(m=>m.title==='通识教育课程');if(base)expand(base.id,null);}
  // Textual requirements supplement the machine fields; preserve their exact source.
  const majorText=nodes.filter(m=>m.origin==='major').map(m=>m.note).join('\n');
  for(const node of nodes){
    node.rule={...node.rule}; node.limit={...node.limit};
    const courseCount=node.note?.match(/(?:选|不少于|至少)(\d+)门/);
    if(courseCount){node.rule.requiredCourseNum=Math.max(n(node.rule.requiredCourseNum),n(courseCount[1]));if(/超过.*专业进阶/.test(node.note))node.limit.courseNumUpperLimit=n(courseCount[1]);}
    const pathCredits=node.note?.match(/^修满(\d+)学分/);
    if(pathCredits)node.rule.requiredCredits=Math.max(n(node.rule.requiredCredits),n(pathCredits[1]));
    node.disabled=false;
    if(/留学生/.test(node.title)&&profile.studentType!=='international'){node.disabled=true;node.disabledReason='留学生专用模块';}
    if(/研究生思想|本硕融通|本博融通/.test(node.title)&&!profile.integration)node.disabled=true;
    if(node.title==='大学外语'){
      const tier=profile.englishTier||'B'; node.rule.requiredCredits=tier==='A'?2:4;
      node.chosenTitle='大学外语（'+tier+'级）';
    }
    if(node.title==='大学英语进阶课程'&&node.parent?.includes('9497491'))node.rule.requiredCredits=2;
    if(node.title==='大学英语基础课程'&&node.parent?.includes('9497499'))node.rule.requiredCredits=2;
    if(node.title==='核心课程七大模块'){
      const m=majorText.match(/七大模块(?:课程)?\s*(\d+)\s*(?:个)?学分/);if(m)node.rule.requiredCredits=n(m[1]);
    }
    if(node.parent && nodes.find(p=>p.id===node.parent)?.title==='核心课程七大模块' && node.title!=='通识微课')node.limit.courseNumUpperLimit=1;
    if(node.title==='艺术创作与审美体验'&&/美育学分不少于2/.test(majorText))node.rule.requiredCredits=2;
    if(node.title==='科学探索与技术创新'&&/回避第五模块/.test(majorText)){node.disabled=true;node.disabledReason='专业方案回避第五模块';}
    if(node.title==='人工智能教学专项'&&(/人工智能/.test(major.title)||/计算与智能创新|大数据学院/.test(major.department||''))){node.disabled=true;node.disabledReason='专业培养已覆盖人工智能课程';}
    if(node.title==='人工智能教学专项'&&!node.disabled){node.rule.requiredCredits=profile.discipline==='humanities'?2:3;node.chosenTitle=profile.discipline==='humanities'?'B2':'B1';}
    if(/路径$/.test(node.title)&&node.parent===null&&node.title!==(profile.development||'专业进阶路径'))node.disabled=true;
    if(node.title==='专业进阶模块'){
      const path=nodes.find(m=>m.title===(profile.development||'专业进阶路径'));
      const base=nodes.find(m=>m.title==='专业进阶路径');
      node.rule.requiredCredits=Math.max(n(path?.rule.requiredCredits),n(path?.rule.showRequiredCredits),profile.development==='荣誉项目路径'?Math.max(n(base?.rule.requiredCredits),n(base?.rule.showRequiredCredits)):0);
      node.pathTitle=profile.development||'专业进阶路径';node.pathNote=path?.note||'';
    }
  }
  for(const node of nodes)if(/路径$/.test(node.title)&&node.parent===null){node.annotationOnly=true;node.rule.requiredCredits=0;node.rule.requiredCourseNum=0;}
  // Explicit branch choices and exemptions come from the user's confirmed audit settings.
  for(const node of nodes){
    const parent=existing.get(node.parent);
    if(parent?.chosenTitle && !node.title.includes(parent.chosenTitle))node.disabled=true;
    const selected=profile.branches?.[node.parent];if(selected&&selected!==node.id)node.disabled=true;
    if(profile.exemptions?.includes(node.id)){node.exempt=true;node.exemptReason='用户录入的已认定免修';}
  }
  for(let i=0;i<nodes.length;i++)for(const node of nodes)if(existing.get(node.parent)?.disabled)node.disabled=true;
  return {id:major.id,title:major.title,source:major.source,completeModules:major.completeModules&&publicPlan.completeModules,nodes};
}
export function normalizeRecords(records,recognitions=[]) {
  const map=new Map(),duplicates=[];
  for(const raw of records){
    if(!raw.code)continue;
    const key=norm(raw.code); const previous=map.get(key);
    const status=['passed','studying','preselected','proposed'].includes(raw.status)?raw.status:'unverified';
    const record={...raw,code:key,credits:Math.max(0,n(raw.credits)),status};
    const priority={passed:5,proposed:4,studying:3,preselected:2,unverified:1};
    if(previous){duplicates.push(key);if(priority[previous.status]>=priority[status])continue;}
    map.set(key,record);
  }
  const targets=new Map();
  for(const r of map.values()){
    const recog=recognitions.find(x=>norm(x.from)===r.code&&x.confirmed===true);
    r.target=recog?norm(recog.to):r.code;r.recognized=!!recog;
    if(targets.has(r.target)){
      const old=targets.get(r.target);duplicates.push(r.code);
      if(({passed:5,proposed:4,studying:3,preselected:2,unverified:1})[old.status]>=({passed:5,proposed:4,studying:3,preselected:2,unverified:1})[r.status])continue;
    }
    targets.set(r.target,r);
  }
  return {records:[...targets.values()],duplicates:[...new Set(duplicates)]};
}
export function auditCurriculum(curriculum, records=[], options={}) {
  const normalized=normalizeRecords(records,options.recognitions),all=normalized.records;
  const current=all.filter(r=>r.status==='passed');
  const forecast=all.filter(r=>r.status==='passed'||r.status==='proposed');
  const nodes=curriculum.nodes.filter(m=>!m.disabled),byId=new Map(nodes.map(m=>[m.id,m]));
  const childMap=new Map(nodes.map(m=>[m.id,nodes.filter(c=>c.parent===m.id)]));
  const roots=nodes.filter(m=>!byId.has(m.parent));
  const root=roots.find(m=>m.title==='方案总览');
  const descend=(id,trail=new Set())=>{if(trail.has(id))return [];trail.add(id);return [byId.get(id),...(childMap.get(id)||[]).flatMap(c=>descend(c.id,new Set(trail)))].filter(Boolean);};
  function calculate(input){
    const assignments=new Map(nodes.map(m=>[m.id,[]])),unallocated=[];
    const choices=[];
    for(const r of input){
      let candidates=nodes.filter(m=>m.courses.some(c=>norm(c.code)===r.target));
      const manual=options.allocations?.[r.code];
      candidates.sort((a,b)=>Number(b.courses.some(c=>norm(c.code)===r.target&&c.required))-Number(a.courses.some(c=>norm(c.code)===r.target&&c.required))||Number(b.origin==='major')-Number(a.origin==='major'));
      if(candidates.length>1)choices.push({code:r.code,chosen:manual||candidates[0].id,choices:candidates.map(m=>({id:m.id,title:m.title}))});
      if(manual)candidates=candidates.filter(m=>m.id===manual);
      let picked=candidates.find(m=>{
        const assigned=assignments.get(m.id),lim=m.limit||{};
        return !(lim.courseNumUpperLimit!=null&&assigned.length>=n(lim.courseNumUpperLimit))&&!(lim.creditsUpperLimit!=null&&sum(assigned.map(x=>x.credits))>=n(lim.creditsUpperLimit));
      });
      if(picked){const cap=picked.limit.creditsUpperLimit;const used=sum(assignments.get(picked.id).map(x=>x.credits));assignments.get(picked.id).push({...r,credits:cap==null?r.credits:Math.min(r.credits,Math.max(0,n(cap)-used))});}else unallocated.push(r);
    }
    // Open elective credits use each record once, after fixed modules have been filled.
    const elective=nodes.find(m=>m.title==='专业进阶模块');
    const path=nodes.find(m=>m.title==='专业进阶路径');
    if(elective&&/全校所有本科生课程中任意选修/.test(path?.note||'')){
      for(const r of [...unallocated])if(/^[A-Z]/.test(r.code)){assignments.get(elective.id).push(r);unallocated.splice(unallocated.indexOf(r),1);}
    }
    const cache=new Map();
    function evaluate(node,trail=new Set()){
      if(cache.has(node.id))return cache.get(node.id);
      if(trail.has(node.id))return {met:false,credits:0,count:0,records:[],id:node.id};
      trail=new Set([...trail,node.id]);
      const children=(childMap.get(node.id)||[]).map(c=>evaluate(c,trail));
      let chosen=children;
      const k=n(node.rule.requiredSubModuleNum);
      if(k>0&&k<children.length&&!node.rule.requireAll&&(k===1||/选一|任选.*模块/.test(node.note||'')))chosen=[...children].sort((a,b)=>Number(b.met)-Number(a.met)||b.credits-a.credits).slice(0,k);
      const unique=new Map([...assignments.get(node.id),...chosen.flatMap(c=>c.records)].map(r=>[r.target,r]));
      // The graduation root counts all distinct credits, including public and development credits.
      if(node.id===root?.id)for(const r of input)unique.set(r.target,r);
      const rs=[...unique.values()],credits=sum(rs.map(r=>r.credits)),count=rs.length;
      const target=n(node.rule.requiredCredits),needed=n(node.rule.requiredCourseNum);
      const mandatory=node.courses.filter(c=>c.required);
      const missing=mandatory.filter(c=>!rs.some(r=>r.target===norm(c.code)));
      const childrenNeeded=k|| (node.rule.requireAll?children.length:0);
      const childMet=children.filter(c=>c.met).length;
      const checks=[];
      if(node.title==='大学外语')checks.push({id:'FET',label:'复旦大学英语水平测试 FET',met:!!options.checks?.FET});
      if(node.title==='实验室安全教育')checks.push({id:'labSafety',label:'在线安全教育、消防培训与相应实验室准入',met:!!options.checks?.labSafety});
      if(node.title==='心理健康教育课程')checks.push({id:'mentalPractice',label:'2 学分课程，或在线课加 16 学时实践 / 1 学分线下课',met:rs.some(r=>r.credits>=2)||rs.length>=2||(rs.length>0&&!!options.checks?.mentalPractice)});
      if(node.title==='体育课程')checks.push({id:'peTerms',label:'四个学期体育必修',met:new Set(rs.map(r=>r.term).filter(Boolean)).size>=4||!!options.checks?.peTerms});
      if(node.pathTitle==='荣誉项目路径'){checks.push({id:'honorSix',label:'至少 6 门荣誉课',met:rs.filter(r=>/H$/i.test(r.code)||/[（(]H[）)]/.test(r.name||'')).length>=6});checks.push({id:'honorRecognition',label:'数学学院荣誉项目认定',met:!!options.checks?.honorRecognition});}
      if(/微专业/.test(node.pathNote||''))checks.push({id:'pathRecognition',label:node.pathTitle==='创新创业路径'?'创新创业微专业及另一非本专业微专业认定':'两个非本专业微专业 / 学程认定',met:!!options.checks?.pathRecognition});
      if(!node.annotationOnly&&/路径|项目/.test(node.title)&&/微专业|荣誉项目修读要求/.test(node.note||''))checks.push({id:node.id+':recognition',label:'路径项目 / 微专业认定',met:!!options.checks?.[node.id+':recognition']});
      const specialRequired=n(node.rule.integrationCreditsRequired)||n(node.rule.postCreditsRequired);
      if(options.integration&&specialRequired)checks.push({id:node.id+':integration',label:'本研融通课程认定',met:!!options.checks?.[node.id+':integration']});
      const required=target>0||needed>0||missing.length>0||childrenNeeded>0||checks.length>0;
      const met=!!node.exempt||(credits>=target&&count>=needed&&!missing.length&&childMet>=childrenNeeded&&checks.every(c=>c.met));
      const result={id:node.id,title:node.title,parent:node.parent,source:node.source,origin:node.origin,credits,count,target,needed,missing,childMet,childrenNeeded,checks,required,met,exempt:!!node.exempt,records:rs,chosenChildren:chosen.map(c=>c.id),note:node.note,rule:node.rule};cache.set(node.id,result);return result;
    }
    nodes.forEach(m=>evaluate(m));
    const rows=[...cache.values()];
    // A/B alternatives are displayed but only the selected branch contributes to completion.
    const inactive=new Set();
    for(const row of rows){const ch=childMap.get(row.id)||[];for(const child of ch)if(!row.chosenChildren.includes(child.id))for(const d of descend(child.id))inactive.add(d.id);}
    for(const r of rows)r.active=!inactive.has(r.id);
    return {rows,unallocated,choices,total:sum(input.map(r=>r.credits)),met:rows.filter(r=>r.required&&r.active).every(r=>r.met),completedRules:rows.filter(r=>r.required&&r.active&&r.met).length,requiredRules:rows.filter(r=>r.required&&r.active).length};
  }
  return {title:curriculum.title,completeModules:curriculum.completeModules,target:n(root?.rule.requiredCredits),current:calculate(current),forecast:calculate(forecast),pending:normalizeRecords(records.filter(r=>r.status!=='proposed'),options.recognitions).records.filter(r=>r.status!=='passed'),duplicates:normalized.duplicates};
}
export function parseTranscript(text,courses=[]) {
  const statuses={'已通过':'passed','在读':'studying','预选':'preselected','待审核':'unverified',passed:'passed',studying:'studying',preselected:'preselected'};
  const records=[],errors=[];
  for(const [i,line] of text.split(/\r?\n/).entries()){
    if(!line.trim())continue;
    const [name,credit,status,term]=line.split(/[,，\t]/).map(s=>s.trim());
    const matches=courses.filter(c=>norm(c.code)===norm(name)||c.name===name);
    const codes=[...new Set(matches.map(c=>c.code))];
    const code=codes.length===1?codes[0]:/^[A-Za-z]+\d+[A-Za-z]*$|^\d+$/.test(name)?name:null;
    if(!code||codes.length>1){errors.push(`第 ${i+1} 行：请使用唯一课程代码`);continue;}
    const candidates=[...new Set(matches.flatMap(c=>c.credits))];
    const credits=credit!==undefined&&credit!==''?Number(credit):candidates.length===1?candidates[0]:NaN;
    if(!Number.isFinite(credits)||credits<0){errors.push(`第 ${i+1} 行：请补充学分`);continue;}
    if(!statuses[status]){errors.push(`第 ${i+1} 行：状态填写已通过 / 在读 / 预选 / 待审核`);continue;}
    records.push({code: norm(code),name:matches[0]?.name||name,credits,status:statuses[status],term:term||''});
  }
  return {records,errors};
}
