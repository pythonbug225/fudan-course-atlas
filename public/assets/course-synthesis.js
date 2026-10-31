(function(){
  'use strict';
  let data={records:[],sources:{}};const byId=new Map();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function text(v){return typeof v==='string'?v:Array.isArray(v)?v.map(text).filter(Boolean).join('；'):''}
  function chosen(g,term='all'){const r=byId.get(g.id);return r?.term_summaries?.[term]||r}
  function profile(g,teacher,term='all'){return (chosen(g,term)?.by_teacher||[]).find(r=>r.teacher===teacher||r.teacher.split(/[、,，]/).map(x=>x.trim()).includes(teacher))}
  function card(g,teachers=[],term='all'){const r=chosen(g,term);return r?(r.card||r.overview||''):g.name+' · 课程资料正在整理。'}
  function comparison(g,teachers,key,term='all'){const r=chosen(g,term);if(!r)return '—';const profiles=(r.by_teacher||[]).filter(p=>teachers.includes(p.teacher)||p.teacher.split(/[、,，]/).every(t=>teachers.includes(t.trim())));if(key==='summary')return profiles.length?profiles.map(p=>p.teacher+'：'+p.summary).join('；'):r.card;const field={teaching:'learning',prereq:'fit'}[key]||key;return profiles.map(p=>text(p[field]||(key==='teaching'?p.summary:''))).filter(Boolean).join('；')||(!r.by_teacher?.length?text(r[field]):'')||'—'}
  function sources(refs){const rs=[...new Set(refs||[])];return rs.length?'<details class="synthesis-sources"><summary>综合依据 · '+rs.length+'项</summary>'+rs.map(key=>'<p>'+esc(data.sources[key]?.label||key)+'</p>').join('')+'</details>':''}
  function renderRecord(r,g,teacher,heading){
    const p=teacher==='all'?null:(r.by_teacher||[]).find(x=>x.teacher===teacher||x.teacher.split(/[、,，]/).map(v=>v.trim()).includes(teacher)),overview=(p?(p.teacher!==teacher?'原资料合并标注教师（'+p.teacher+'）：':'')+p.summary:'')||(teacher!=='all'&&r.learning?r.learning:r.overview||r.card);
    let out='<section class="detail-note course-synthesis"><h3>'+esc(heading)+'</h3><p class="verdict">'+esc(overview)+'</p>';
    const fields=[['learning','课程主线'],['workload','主要投入'],['assessment','考核安排'],['grading','给分与考试反馈'],['fit','选课与准备']];
    for(const [k,label] of fields){const value=text(p?p[k]:r[k]);if(value&&value!==overview)out+='<div class="field"><b>'+label+'</b><p>'+esc(value)+'</p></div>'}
    if(teacher==='all'&&r.by_teacher?.length)out+='<div class="teacher-synthesis">'+r.by_teacher.map(t=>'<article><h4>'+esc(t.teacher)+(t.teacher.split(/[、,，]/).every(n=>g.teachers.includes(n.trim()))?'':(g.course_syllabus_references||[]).some(r=>t.teacher.split(/[、,，]/).every(n=>r.teachers.includes(n.trim())))?' <span class="meta">参考大纲</span>':' <span class="meta">历史资料</span>')+'</h4><p>'+esc(t.summary)+'</p>'+[['workload','投入'],['assessment','考核'],['grading','成绩反馈']].filter(([k])=>text(t[k])).map(([k,l])=>'<p><b>'+l+'：</b>'+esc(text(t[k]))+'</p>').join('')+'</article>').join('')+'</div>';
    if(r.discussion_takeaways?.length)out+='<div class="field"><b>讨论中的备考线索</b>'+r.discussion_takeaways.map(v=>'<p>'+esc(v)+'</p>').join('')+'</div>';
    out+=sources(p?.source_refs?.length?p.source_refs:r.source_refs);
    if(r.gaps?.length)out+='<details class="synthesis-gaps"><summary>资料缺项</summary>'+r.gaps.map(v=>'<p>'+esc(text(v))+'</p>').join('')+'</details>';
    return out+'</section>';
  }
  function summary(g,teacher='all',term='all'){
    const base=byId.get(g.id);if(!base)return '<section class="detail-note"><h3>课程综合描述</h3><p>'+esc(g.name)+'的综合描述正在整理。</p></section>';
    if(term!=='all')return renderRecord(chosen(g,term),g,teacher,(base.term_summaries?.[term]||base.scope_term===term?term+' · ':'')+'课程综合描述');
    const terms=Object.entries(base.term_summaries||{}).filter(([_,r])=>teacher==='all'||r.by_teacher?.some(t=>t.teacher===teacher||t.teacher.split(/[、,，]/).map(n=>n.trim()).includes(teacher)));
    let out=(base.official_syllabus_only&&terms.length||teacher!=='all'&&!base.by_teacher?.some(t=>t.teacher===teacher||t.teacher.split(/[、,，]/).map(n=>n.trim()).includes(teacher))&&terms.length)?'':renderRecord(base,g,teacher,base.scope_term?base.scope_term+' · 课程综合描述':'课程综合描述');
    for(const [key,row] of terms)out+=renderRecord(row,g,teacher,key+' · 课程综合描述');return out;
  }
  async function loadSummaries(){const packed=window.COURSE_DATA_COMPRESSED===true,r=await fetch('data/course-summaries.json'+(packed?'.gz':''));if(!r.ok)throw Error('课程综合描述未载入');if(!packed)return r.json();const b=new Uint8Array(await r.arrayBuffer());if(b[0]!==31||b[1]!==139)return JSON.parse(new TextDecoder().decode(b));if(typeof DecompressionStream==='function'){const stream=new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text())}const fallback=await fetch('https://raw.githubusercontent.com/pythonbug225/fudan-course-atlas/main/public/data/course-summaries.json');if(!fallback.ok)throw Error('课程综合描述未载入');return fallback.json()}
  window.CourseSynthesis={async init(){data=await loadSummaries();for(const row of data.records)byId.set(row.id,row)},card,summary,profile,comparison,sourceCount:(g,term='all')=>(chosen(g,term)?.source_refs||[]).length,teachers:g=>[...new Set([byId.get(g.id),...Object.values(byId.get(g.id)?.term_summaries||{})].flatMap(r=>(r?.by_teacher||[]).flatMap(p=>p.teacher.split(/[、,，]/).map(n=>n.trim()))))]};
})();
