(function(){
  'use strict';
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const credit=v=>v!==null&&v!==undefined&&String(v).trim()!==''&&Number.isFinite(Number(v))&&Number(v)>=0;
  function render(g,offers){
    const os=offers||g.offerings||[],values=[...new Set(os.filter(o=>credit(o.credits)).map(o=>Number(o.credits)))].sort((a,b)=>a-b);
    if(!os.length&&g.history_only&&credit(g.plan_credits))values.push(Number(g.plan_credits));
    const creditText=values.length?values.join(' / ')+' 学分'+(values.length>1?'（分班不同）':os.some(o=>!credit(o.credits))?'（部分班待补）':''):'学分待补';
    const departments=[...new Set(os.length?os.map(o=>o.department).filter(Boolean):(g.history_only?g.departments||[]:[]))];
    const departmentText=departments.length?departments.join(' / ')+(departments.length>1?'（分班开设）':'')+(os.some(o=>!o.department)?' · 部分班待补':''):'待补充';
    const levels=[...new Set(os.map(o=>o.course_level).filter(Boolean))];
    const missing=g.student_evaluation?.has_reviews===false?'<span class="course-no-reviews">暂无已核实学生评价</span>':'';
    const cancelled=os.length&&os.every(o=>o.cancelled)?'<span class="course-cancelled">预排表注明停开</span>':'';
    return '<div class="course-facts"><span class="course-credit"'+(g.credits_source?' title="'+esc(g.credits_source)+'"':'')+'>'+esc(creditText)+'</span>'+(g.english_level?'<span class="course-english-level" title="'+esc(g.english_level_source)+'">英语 · '+esc(g.english_level)+'</span>':'')+(levels.length?'<span class="course-level">'+esc(levels.join(' / '))+'</span>':'')+missing+cancelled+'</div><p class="course-department">开课院系：'+esc(departmentText)+'</p>';
  }
  window.CourseMeta={render};
})();
