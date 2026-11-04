(function(){
 'use strict';
 let index=null;const docs=new Map();
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const clip=(s,n)=>{s=String(s||'').trim();if(s.length<=n)return s;const head=s.slice(0,n),last=Math.max(head.lastIndexOf('。'),head.lastIndexOf('；'));return last>n*.45?head.slice(0,last+1):head.replace(/[，、；：, ]+$/,'')+'…';};
 const assessment=d=>(d.assessment||[]).filter(a=>Number(a.percentage)>0).map(a=>a.criteria+' '+a.percentage+'%').join('；');
 async function load(path){return window.CourseDataJSON?window.CourseDataJSON.load(path):fetch(path).then(r=>{if(!r.ok)throw Error(path);return r.json()});}
 async function init(){
  const candidate=await load('data/syllabus-fallback.json');if(!Array.isArray(candidate.parts)||!candidate.parts.every(p=>/^syllabus-fallback-\d+\.json$/.test(p)))throw Error('大纲参考目录无效');
  const parts=await Promise.all(candidate.parts.map(p=>load('data/'+p)));for(const p of parts)for(const [id,d]of Object.entries(p.documents||{}))docs.set(id,d);
  if(docs.size!==candidate.counts.documents)throw Error('大纲参考未完整载入');index=candidate;return true;
 }
 function has(g){return g.student_evaluation?.has_reviews===false&&Boolean(index?.courses[g.id]);}
 function rows(g,term='all',teacher='all',strict=false){
  if(!has(g))return[];let rs=index.courses[g.id].lesson_ids.map(id=>docs.get(id)).filter(Boolean);
  if(term!=='all'){const exact=rs.filter(d=>d.term===term);rs=exact.length||strict?exact:rs;}
  if(teacher!=='all'){const names=Array.isArray(teacher)?teacher:[teacher];rs=rs.filter(d=>names.every(t=>d.teachers.includes(t)));}
  return rs;
 }
 function card(g,teachers=[],term='all'){
  const all=rows(g,term),exact=teachers.length?all.filter(d=>d.teachers.some(t=>teachers.includes(t))):all,d=(exact.length?exact:all)[0];if(!d)return'';
  const reference=index.courses[g.id].reference_ids.includes(d.id)||(term!=='all'&&d.term!==term)||teachers.length&&!exact.length;
  return d.term+' '+d.teachers.slice(0,2).join('、')+(d.teachers.length>2?'等'+d.teachers.length+'位教师':'')+(reference?'参考大纲':'大纲')+'：'+clip(d.learning||d.method||assessment(d),150)+(d.learning&&assessment(d)?' 考核：'+clip(assessment(d),100)+'。':'');
 }
 function grouped(rs){
  const groups=new Map();for(const d of rs){const key=JSON.stringify([d.term,[...d.teachers].sort(),d.learning,d.method,d.tasks,d.assessment,d.prereq,d.schedule,d.assessment_notes]);if(!groups.has(key))groups.set(key,{...d,sections:[],sources:[]});const p=groups.get(key);p.sections.push(d.section_code);p.sources.push(d.source_label);}
  return[...groups.values()];
 }
 function summary(g,teacher='all',term='all'){
  if(!has(g))return'';const rs=rows(g,term,teacher,term!=='all');
  if(!rs.length)return '<section class="detail-note course-synthesis"><h3>官方大纲参考</h3><p>'+esc(teacher==='all'?'所选学期尚未保存本班大纲。':'尚未保存'+teacher+'班的大纲。')+'已保存的其他班次可在“课程大纲”查看。</p></section>';
  return '<section class="detail-note syllabus-reference"><h3>官方大纲整理</h3><p class="meta">暂无已核实学生评价 · 按教师、学期和班次整理大纲</p>'+grouped(rs).map(d=>{
   const ref=index.courses[g.id].reference_ids.includes(d.id);let out='<article class="syllabus-profile"><h4>'+esc(d.term+' · '+d.teachers.join('、'))+(ref?' · 参考班次':'')+'</h4><p class="meta">'+esc(d.sections.join(' / '))+'</p>';
   for(const [title,value]of [['课程主线',d.learning],['课堂与学习方式',d.method],['作业与主要任务',d.tasks],['考核安排',assessment(d)],['考核细节',d.assessment_notes&&d.assessment_notes!==d.tasks?d.assessment_notes:''],['先修要求',d.prereq]])if(value)out+='<div class="field"><b>'+title+'</b><p>'+esc(value)+'</p></div>';
   if(d.schedule&&d.schedule!==d.learning)out+='<details><summary>教学内容与进度要点</summary><p>'+esc(d.schedule)+'</p></details>';
   out+='<details class="synthesis-sources"><summary>来源与保存版本</summary>'+d.sources.map(s=>'<p>'+esc(s)+'</p>').join('')+'<p>保存日期：'+esc(d.saved_at||'条目未标注')+'</p></details></article>';return out;
  }).join('')+'</section>';
 }
 function comparison(g,teachers,key,term='all'){
  if(!has(g))return'';const rs=rows(g,term,teachers,term!=='all');if(!rs.length)return'暂无本班大纲摘要';
  return grouped(rs).map(d=>key==='summary'?clip(d.learning||d.method||assessment(d),240):key==='teaching'?d.learning:key==='workload'?[d.method,d.tasks].filter(Boolean).join('；'):key==='assessment'?assessment(d):key==='prereq'?d.prereq:key==='grading'?'本班大纲列出的成绩构成：'+(assessment(d)||'未列具体比例'):'').filter(Boolean).join('；')||'大纲未说明';
 }
 window.SyllabusFallback={init,has,card,summary,comparison,sourceCount:(g,term='all')=>rows(g,term).length,teachers:g=>[...new Set(rows(g).flatMap(d=>d.teachers))]};
})();
