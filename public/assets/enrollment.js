(function(){
  'use strict';
  let data=null,loading=null;const byCourse=new Map(),chosenTerm=new Map();
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const termRank=s=>Number(String(s).slice(0,4))*3+(String(s).includes('秋')?2:String(s).includes('暑')?1:0);
  async function init(){
    if(loading)return loading;
    loading=fetch('data/enrollment.json').then(r=>{if(!r.ok)throw Error('enrollment '+r.status);return r.json()}).then(d=>{data=d;for(const r of d.records||[])for(const cid of r.course_ids||[]){if(!byCourse.has(cid))byCourse.set(cid,[]);byCourse.get(cid).push(r)}return true}).catch(()=>false);
    return loading;
  }
  function rows(id){return byCourse.get(id)||[]}
  function render(g,teacher='all'){
    if(!data)return '<section class="detail-resource enrollment-panel"><h3>往期选课人数</h3><p class="meta">选课人数暂未载入，可稍后刷新页面重试。</p></section>';
    const all=rows(g.id),terms=[...new Set(all.map(r=>r.term))].sort((a,b)=>termRank(b)-termRank(a));
    if(!terms.length)return '<section class="detail-resource enrollment-panel"><h3>往期选课人数</h3><p>本课程暂未匹配到可确认的历史教学班人数。</p><p class="meta">来源：复旦教务系统课程查询 · '+esc(data.as_of?.slice(0,10))+'</p></section>';
    const term=chosenTerm.get(g.id)&&terms.includes(chosenTerm.get(g.id))?chosenTerm.get(g.id):terms[0];
    const peers=all.filter(r=>r.term===term),visible=peers.filter(r=>teacher==='all'||r.teachers.includes(teacher));
    const types=[...new Set(visible.map(r=>r.class_type||'未标班型'))];
    let html='<section class="detail-resource enrollment-panel" data-enrollment-course="'+esc(g.id)+'"><div class="enrollment-heading"><h3>往期选课人数</h3><label>学期 <select data-enrollment-term="'+esc(g.id)+'">'+terms.map(t=>'<option'+(t===term?' selected':'')+'>'+esc(t)+'</option>').join('')+'</select></label></div>';
    html+='<p class="meta">教务已选人数 / 人数上限。切换学期比较；选择“全部教师”可看同课平行班。</p>';
    if(!visible.length)html+='<p>该学期没有匹配到所选教师的教学班，可切换学期或查看全部教师。</p>';
    for(const type of types){
      const group=visible.filter(r=>(r.class_type||'未标班型')===type),allGroup=peers.filter(r=>(r.class_type||'未标班型')===type),total=allGroup.reduce((s,r)=>s+r.std_count,0);
      html+='<div class="enrollment-group"><h4>'+esc(type)+' <span class="meta">'+allGroup.length+'个班 · 共'+total+'人</span></h4>';
      for(const r of group){
        const hasCap=r.limit_count>0,ratio=hasCap?r.std_count/r.limit_count:null,share=total>0?r.std_count/total:null;
        html+='<article class="enrollment-row" data-enrollment-section="'+esc(r.section_code)+'"><div class="enrollment-row-top"><b>'+esc(r.teachers.join('、')||'教师未注明')+'</b><strong>'+r.std_count+' / '+(hasCap?r.limit_count:'未注明')+' 人</strong></div><div class="enrollment-bar" aria-hidden="true"><i style="width:'+(hasCap?Math.min(100,ratio*100):0)+'%"></i></div><p class="enrollment-caption">'+esc(r.section_code)+' · '+(hasCap?'容量使用率 '+(ratio*100).toFixed(1)+'%'+(ratio>1?'（系统返回人数超过返回上限）':''):'容量未注明，不计算比例')+(allGroup.length>1&&share!==null?' · 本组人数占比 '+(share*100).toFixed(1)+'%':'')+'</p>';
        if(!hasCap&&r.planned_capacity)html+='<p class="meta">课程表预排人数 '+esc(r.planned_capacity)+'；不作为当前系统上限。</p>';
        if(r.snapshot_as_of)html+='<p class="meta">该班快照：'+esc(r.snapshot_as_of)+'</p>';
        if(r.capacity_snapshot_as_of&&r.capacity_snapshot_as_of!==r.snapshot_as_of)html+='<p class="meta">人数上限快照：'+esc(r.capacity_snapshot_as_of)+'</p>';
        if(r.schedule_hint)html+='<details class="enrollment-schedule"><summary>上课时间与地点</summary><p>'+esc(r.schedule_hint)+'</p></details>';
        html+='</article>';
      }
      html+='</div>';
    }
    return html+'<p class="enrollment-context">人数也受必修安排、上课时间、班型和选课对象影响，不等同于第一志愿偏好、抽签概率或教师好评。联合授课按整个教学班展示。</p><p class="source-label">来源：复旦教务系统课程查询 · '+esc(data.as_of?.slice(0,10))+'为默认快照日期；单个班次另有标注时以该班日期为准。未保存选课过程中的历次变化。</p></section>';
  }
  window.EnrollmentStats={init,render,rows,teachers:g=>[...new Set(rows(g.id).flatMap(r=>r.teachers))],setTerm:(id,term)=>chosenTerm.set(id,term)};
})();
