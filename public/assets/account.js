'use strict';
(() => {
  let state = { status: 'loading', signedIn: false, isModerator: false, user: null };
  let pending;
  const all = selector => document.querySelectorAll(selector);
  const text = (selector, value) => all(selector).forEach(el => { el.textContent = value; });
  function updateLinks() {
    const returnTo = location.pathname + location.search + location.hash;
    all('[data-auth-signin]').forEach(el => { el.href = '/login.html?return_to=' + encodeURIComponent(returnTo); });
  }
  function render() {
    const ready = state.status === 'ready';
    all('[data-auth-guest]').forEach(el => { el.hidden = !ready || state.signedIn; });
    all('[data-auth-member]').forEach(el => { el.hidden = !ready || !state.signedIn; });
    all('[data-auth-loading]').forEach(el => { el.hidden = state.status !== 'loading'; });
    all('[data-auth-error]').forEach(el => { el.hidden = state.status !== 'error'; });
    all('[data-auth-moderator]').forEach(el => { el.hidden = !ready || !state.isModerator; });
    all('[data-auth-student]').forEach(el => { el.hidden = !ready || !state.signedIn || !state.user?.studentNumber; });
    text('[data-auth-name]', state.user?.displayName || '选课同学');
    text('[data-auth-email]', state.user?.studentNumber ? '学号 ' + state.user.studentNumber : '网站管理员');
    text('[data-auth-role]', state.isModerator ? '投稿审核员' : '校内注册用户');
    text('[data-account-balance]', state.signedIn && window.FudanPoints?.getState().signedIn ? window.FudanPoints.getState().balance + ' 分' : '—');
    updateLinks();
  }
  async function refresh() {
    if (pending) return pending;
    pending = (async () => {
      try {
        const response = await fetch('/api/session', { credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(10000) });
        if (!response.ok) throw Error('session_unavailable');
        const data = await response.json();
        state = { status: 'ready', signedIn: Boolean(data.signedIn), isModerator: Boolean(data.isModerator), user: data.user || null };
      } catch {
        state = { status: 'error', signedIn: false, isModerator: false, user: null };
      }
      render();
      window.dispatchEvent(new CustomEvent('auth-changed', { detail: { ...state } }));
      return { ...state };
    })();
    try { return await pending; } finally { pending = null; }
  }
  document.addEventListener('click', async event => {

    const logout = event.target.closest('[data-student-logout]');
    if (logout) { logout.disabled = true; try { await authApi('logout', {}); location.assign('/login.html'); } catch (e) { logout.disabled = false; window.alert(e.message); } }
    if (event.target.closest('[data-refresh-accounts]')) void loadAccounts();
    const decision = event.target.closest('[data-account-decision]');
    if (decision) {
      decision.disabled = true;
      const card = decision.closest('[data-account-id]');
      try { await authApi('decision', {id:card.dataset.accountId,status:decision.dataset.accountDecision,note:card.querySelector('input').value}); await loadAccounts(); }
      catch (e) { card.querySelector('[role=status]').textContent = e.message; decision.disabled = false; }
    }
    if (event.target.closest('[data-auth-retry]')) {
      state.status = 'loading'; render(); void refresh();
    }
  });
  window.addEventListener('hashchange', updateLinks);
  window.addEventListener('pageshow', event => { if (event.persisted) void refresh(); });
  window.addEventListener('points-changed', render);
  window.addEventListener('auth-changed', event => { if (event.detail.isModerator) void loadAccounts(); });

  async function authApi(path, body) {
    const response = await fetch('/api/auth/' + path, {method:body?'POST':'GET',credentials:'same-origin',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(15000)});
    const data = await response.json(); if (!response.ok) throw Error(data.error || '操作失败，请重试。'); return data;
  }
  async function loadAccounts() {
    const list = document.querySelector('#account-approval-list');
    list.replaceChildren();
    try {
      const data = await authApi('accounts?status=' + document.querySelector('#account-status-filter').value);
      if (!data.accounts.length) { list.textContent = '这个分类下暂时没有账号。'; return; }
      for (const account of data.accounts) {
        const card = document.createElement('article'); card.className = 'submission-card'; card.dataset.accountId = account.id;
        const title = document.createElement('b'); title.textContent = account.student_number + ' · ' + account.nickname; card.append(title);
        const date = document.createElement('p'); date.className = 'meta'; date.textContent = '注册于 ' + account.created_at.slice(0,10); card.append(date);
        const label = document.createElement('label'); label.textContent = '审核反馈'; const note = document.createElement('input'); note.maxLength = 300; note.value = account.review_note || ''; label.append(note); card.append(label);
        const actions = document.createElement('div'); actions.className = 'account-actions';
        for (const [status, text] of [['approved','通过注册'],['rejected','退回申请'],['suspended','停用账号']]) {
          if (status === account.status) continue;
          const button = document.createElement('button'); button.className = 'secondary'; button.dataset.accountDecision = status; button.textContent = text; actions.append(button);
        }
        card.append(actions); const message = document.createElement('p'); message.setAttribute('role','status'); card.append(message); list.append(card);
      }
    } catch (e) { list.textContent = e.message; }
  }
  document.querySelector('#account-status-filter').addEventListener('change', loadAccounts);
  document.querySelector('#change-password-form').addEventListener('submit', async event => {
    event.preventDefault(); const form = event.target, message = document.querySelector('#password-status'), button = form.querySelector('button');
    const body = Object.fromEntries(new FormData(form));
    if (body.password !== body.confirmPassword) { message.textContent = '两次新密码不一致。'; return; }
    delete body.confirmPassword; button.disabled = true;
    try { await authApi('password', body); form.reset(); message.textContent = '密码已更新，其他设备的登录已退出。'; }
    catch (e) { message.textContent = e.message; } finally { button.disabled = false; }
  });

  window.FudanAuth = { refresh, getState: () => ({ ...state }) };
  render();
  window.FudanAuth.ready = refresh();
})();
