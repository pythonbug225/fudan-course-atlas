'use strict';
(() => {
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {pending:'待审核',approved:'审核通过',rejected:'已退回',withdrawn:'已撤回',legacy:'历史已公开'};
  let signedIn = false, moderator = false;
  async function api(url, options) {
    const response = await fetch(url, {credentials:'same-origin', ...options});
    const data = await response.json();
    if (!response.ok) throw Error(data.error || '操作失败，请重试。');
    return data;
  }
  function courseName(id) {
    const course = typeof D !== 'undefined' && D?.scope?.find(c => c.id === id);
    return course ? `${course.code} · ${course.name}` : id;
  }
  function card(row, review) {
    const fields = [['overall','综合内容'],['learning','学习收获'],['workload','作业与用时'],['assessment','考核'],['grading','给分体验']];
    return `<article class="submission-card" data-submission="${esc(row.id)}"><div class="submission-heading"><b>${esc(courseName(row.course_id))}</b><span class="tag">${labels[row.status] || esc(row.status)}</span></div><p class="meta">${row.kind==='material'?'课程资料':'课程评价'} · ${esc(row.teacher)} · ${esc(row.term)} · ${esc(row.nickname)} · ${esc(row.created_at.slice(0,10))}</p>${review ? fields.filter(([key])=>row[key]).map(([key,title])=>`<div class="field"><b>${title}</b><p>${esc(row[key])}</p></div>`).join('') : `<p>${esc(row.overall)}</p>`}${row.moderation_note?`<p class="submission-feedback"><b>审核意见：</b>${esc(row.moderation_note)}</p>`:''}${review ? (row.files || []).map(f=>`<p><a href="/api/attachments/${encodeURIComponent(f.id)}" target="_blank" rel="noopener noreferrer">查看附件：${esc(f.name)}</a></p>`).join('') : ''}${review && row.status==='pending' ? `<label>审核说明<input data-review-note maxlength="1000" placeholder="退回时请说明需要补充什么"/></label><div class="submission-actions"><button class="primary" data-review-decision="approved" type="button">通过并奖励 ${row.kind==='material'?10:20} 分</button><button class="secondary" data-review-decision="rejected" type="button">退回修改</button></div>` : !review && row.status!=='withdrawn' ? '<button class="text-button" data-withdraw-submission type="button">撤回投稿</button>' : ''}<p data-submission-status role="status" aria-live="polite"></p></article>`;
  }
  async function refreshMine() {
    const box = $('#my-submission-list');
    if (!box) return;
    if (!signedIn) { box.textContent='登录后查看你的投稿与审核进度。'; return; }
    try {
      const data = await api('/api/submissions/mine');
      box.innerHTML = data.submissions.length ? data.submissions.map(row=>card(row,false)).join('') : '<p class="meta">还没有投稿。分享具体的修读经历或资料，审核通过后即可获得积分。</p>';
    } catch (e) { box.textContent=e.message; }
  }
  async function refreshQueue() {
    if (!moderator) return;
    const box = $('#moderation-list');
    try {
      const data = await api('/api/moderation?status='+encodeURIComponent($('#moderation-status').value));
      box.innerHTML = data.submissions.length ? data.submissions.map(row=>card(row,true)).join('') : '<p class="meta">这个状态下暂无投稿。</p>';
    } catch (e) { box.textContent=e.message; }
  }
  document.addEventListener('click', async event => {
    const refresh = event.target.closest('[data-refresh-submissions]');
    if (refresh) { await refreshMine(); await refreshQueue(); return; }
    const action = event.target.closest('[data-review-decision],[data-withdraw-submission]');
    if (!action) return;
    const article=action.closest('[data-submission]'), status=article.querySelector('[data-submission-status]');
    const decision=action.dataset.reviewDecision;
    if (!decision && action.dataset.confirm !== 'yes') { action.dataset.confirm='yes'; action.textContent='再次点击确认撤回'; status.textContent='撤回后停止公开展示，并收回本篇已发放的奖励。'; return; }
    const reason=article.querySelector('[data-review-note]')?.value.trim() || '';
    if (decision==='rejected' && !reason) { status.textContent='请先填写退回修改的建议。'; return; }
    action.disabled=true; status.textContent='正在保存…';
    try {
      if (decision) await api('/api/moderation',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:article.dataset.submission,decision,reason})});
      else await api('/api/reviews/'+encodeURIComponent(article.dataset.submission),{method:'DELETE'});
      await refreshMine(); await refreshQueue(); await window.FudanPoints?.refresh?.();
    } catch(e) { status.textContent=e.message; action.disabled=false; }
  });
  async function init() {
    try {
      const session=await window.FudanAuth.ready; signedIn=session.signedIn; moderator=session.isModerator;
      $('#moderation-center').hidden=!moderator;
      $('#moderation-status').addEventListener('change',refreshQueue);
      await refreshMine(); await refreshQueue();
    } catch(e) { $('#my-submission-list').textContent=e.message; }
  }
  window.addEventListener('auth-changed',event=>{signedIn=event.detail.signedIn;moderator=event.detail.isModerator;$('#moderation-center').hidden=!moderator;void refreshMine();void refreshQueue();});
  window.addEventListener('community-submitted',()=>{void refreshMine();void refreshQueue();});
  window.SubmissionCenter={refreshMine,refreshQueue,ready:init()};
})();
