'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const message = text => { $('#auth-message').textContent = text; };
  let recoveryCode = '';
  function mode(name) {
    ['login','register','recover'].forEach(value => { $('#panel-' + value).hidden = name !== value; });
    document.querySelectorAll('[role=tab]').forEach(tab => tab.setAttribute('aria-selected', String(tab.dataset.mode === name)));
    message('');
  }
  async function api(path, body) {
    const response = await fetch('/api/auth/' + path, { method: body ? 'POST' : 'GET', credentials: 'same-origin', cache: 'no-store', headers: body ? { 'Content-Type':'application/json' } : {}, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(15000) });
    const data = await response.json();
    if (!response.ok) throw Error(data.error || '操作未完成，请重试。');
    return data;
  }
  function showRecovery(value) { recoveryCode = value; $('#recovery-code').textContent = value; $('#recovery-box').hidden = false; }
  function destination() {
    const value = new URLSearchParams(location.search).get('return_to');
    try { const url = new URL(value || '/index.html', location.origin); return url.origin === location.origin && !url.pathname.startsWith('/api/') && url.pathname !== '/login.html' ? url.pathname + url.search + url.hash : '/index.html'; } catch { return '/index.html'; }
  }
  function showStatus(data, redirect = false) {
    if (data.signedIn) { if (redirect) location.assign(destination()); return; }
    if (!data.user) { $('#pending-box').hidden = true; return; }
    $('#pending-box').hidden = false;
    $('#account-state-heading').textContent = data.user.status === 'pending' ? '账户审核中' : '账号暂未开放访问';
    $('#account-state-note').textContent = data.user.reviewNote || '管理员通过后，使用学号和本站密码登录即可进入。';
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => mode(button.dataset.mode)));
  document.querySelectorAll('[data-auth-form]').forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(form));
    if (body.confirmPassword !== undefined && body.password !== body.confirmPassword) { message('两次密码输入不一致。'); return; }
    delete body.confirmPassword;
    const action = form.dataset.authForm, button = form.querySelector('[type=submit]');
    button.disabled = true; message('正在处理…');
    try {
      body.returnTo = destination();
      const data = await api(action, body);
      form.querySelectorAll('[type=password]').forEach(field => { field.value = ''; });
      if (data.recoveryCode) showRecovery(data.recoveryCode);
      if (action === 'login') {
        if (data.user.status === 'approved') { location.assign(data.returnTo || destination()); return; }
        showStatus({user:data.user}); message('登录成功，账户正在等待审核。');
      } else if (action === 'register') { showStatus({user:data.user}); message('注册成功。请先保存下方恢复码，再等待管理员审核。'); }
      else { mode('login'); message('密码已重设，请保存新的恢复码并重新登录。'); }
    } catch (error) { message(error.name === 'TimeoutError' ? '连接较慢，请重试。' : error.message); }
    finally { button.disabled = false; }
  }));
  $('#save-recovery').addEventListener('click', () => {
    const blob = new Blob(['复旦选课地图账户恢复码\n' + recoveryCode + '\n请妥善保存，不要公开分享。'], {type:'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = '选课地图账户恢复码.txt'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('#refresh-state').addEventListener('click', async () => { try { showStatus(await api('status'), true); } catch (e) { message(e.message); } });
  $('#leave-account').addEventListener('click', async () => { try { await api('logout', {}); $('#pending-box').hidden = true; message('已退出。'); } catch (e) { message(e.message); } });
  api('status').then(data => showStatus(data)).catch(() => {});
})();
