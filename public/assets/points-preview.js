'use strict';
(() => {
  const $ = (selector) => document.querySelector(selector);
  const tiers = [
    { name: '同行者', threshold: 0 },
    { name: '共建伙伴', threshold: 50 },
    { name: '课程共建者', threshold: 150 },
  ];
  const state = { loaded: false, signedIn: false, balance: null, checkedInToday: false, events: [] };
  let checkingIn = false;

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);

  function setText(selector, value) {
    const element = $(selector);
    if (element) element.textContent = value;
  }

  function render() {
    const balance = state.balance;
    setText('#points-balance-value', balance === null ? '—' : String(balance));
    document.querySelectorAll('[data-points-login]').forEach((login) => {
      login.hidden = state.loaded && state.signedIn;
    });

    const button = $('[data-checkin]');
    if (button) {
      button.disabled = !state.signedIn || state.checkedInToday || checkingIn;
      button.textContent = checkingIn ? '正在记账…' : state.checkedInToday ? '今日已签到' : '立即签到 · +5 分';
    }

    if (state.error) {
      setText('#points-checkin-status', state.error);
    } else if (!state.loaded) {
      setText('#points-checkin-status', '正在读取账户积分…');
    } else if (!state.signedIn) {
      setText('#points-checkin-status', '登录后可签到；课程资料仍可免费浏览。');
    } else {
      setText('#points-checkin-status', state.checkedInToday ? '今日签到已由服务端确认。' : '每日签到 +5 分，积分记入你的账户。');
    }

    const currentTier = [...tiers].reverse().find((tier) => balance !== null && balance >= tier.threshold) || tiers[0];
    const nextTier = tiers.find((tier) => tier.threshold > currentTier.threshold);
    const target = nextTier ? nextTier.threshold : currentTier.threshold;
    const remaining = balance === null ? null : Math.max(0, target - balance);
    const fill = $('#points-progress-fill');
    if (fill) fill.style.width = balance === null ? '0%' : `${target ? Math.max(0, Math.min(100, (balance / target) * 100)) : 100}%`;
    const track = $('.points-progress-track');
    if (track) track.setAttribute('aria-label', remaining === null ? '读取积分后显示等级进度' : nextTier ? `距离下一等级还差${remaining}分` : '已达到课程共建者等级');
    setText('#points-level-current', `当前：${currentTier.name}`);
    setText('#points-level-name', currentTier.name);
    setText('#points-next-label', nextTier ? `距离升级为「${nextTier.name}」` : '当前展示称号');
    setText('#points-next-remaining', remaining === null ? '—' : nextTier ? `还差 ${remaining} 分` : '已达成');
    setText('#points-progress-value', balance === null ? '—' : nextTier ? `${balance} / ${target} 分` : `${balance} 分`);
    document.querySelectorAll('[data-points-level]').forEach((row) => {
      row.classList.toggle('active-rank', row.dataset.pointsLevel === currentTier.name);
    });

    const history = $('#points-activity-list');
    if (history) {
      if (!state.signedIn) {
        history.innerHTML = '<p class="points-empty">登录后可查看个人积分流水。</p>';
      } else if (!state.events.length) {
        history.innerHTML = '<p class="points-empty">目前还没有积分记录。每日签到可获得 5 分。</p>';
      } else {
        history.innerHTML = state.events.map((event) => {
          const isCheckIn = event.eventType === 'checkin';
          const title = ({checkin:'每日签到',exam_unlock:'试卷文件解锁',submission_reward:'投稿审核奖励',submission_withdrawal:'投稿撤回 · 奖励收回'})[event.eventType] || '积分变动';
          const detail = isCheckIn ? '账户签到奖励' : `${event.eventType==='exam_unlock'?'文件':'投稿'}编号 ${escapeHtml(event.referenceId || '—')}`;
          const date = event.createdAt ? new Date(event.createdAt).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', dateStyle: 'medium', timeStyle: 'short' }) : '时间未知';
          const delta = Number(event.delta);
          return `<article class="points-activity-row"><div><b>${title}</b><span>${detail}</span></div><time>${escapeHtml(date)}</time><strong>${delta > 0 ? '+' : '−'}${Math.abs(delta)}</strong></article>`;
        }).join('');
      }
    }
  }

  async function refresh() {
    state.error = '';
    try {
      const response = await fetch('/api/points', { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) throw new Error('积分服务暂不可用，请稍后刷新。');
      const data = await response.json();
      state.loaded = true;
      state.signedIn = Boolean(data.signedIn);
      state.balance = state.signedIn ? Number(data.balance) : null;
      state.checkedInToday = Boolean(data.checkedInToday);
      state.events = Array.isArray(data.events) ? data.events : [];
    } catch {
      state.error = '积分服务暂不可用，暂时无法确认签到状态或账户余额。';
      state.loaded = false;
      state.balance = null;
    }
    render();
    window.dispatchEvent(new Event('points-changed'));
    return { ...state };
  }

  async function checkIn() {
    if (!state.signedIn) {
      setText('#points-checkin-status', '请先登录，再使用每日签到。');
      const login = $('[data-points-login]');
      if (login) login.hidden = false;
      return false;
    }
    if (checkingIn || state.checkedInToday) return false;
    checkingIn = true;
    state.error = '';
    render();
    try {
      const response = await fetch('/api/points/checkin', {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: '{}',
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          state.signedIn = false;
          const login = $('[data-points-login]');
          if (login) login.hidden = false;
        }
        throw new Error(response.status === 503 ? '积分服务暂不可用，签到没有记账。' : '签到未成功，请登录后重试。');
      }
      state.balance = Number(data.balance);
      state.checkedInToday = true;
      state.loaded = true;
      render();
      setText('#points-checkin-status', data.alreadyCheckedIn ? '今天已经签到过，本次没有重复增加积分。' : '签到完成，服务端已记入 +5 分。');
      await refresh();
      setText('#points-checkin-status', data.alreadyCheckedIn ? '今天已经签到过，本次没有重复增加积分。' : '签到完成，服务端已记入 +5 分。');
      return true;
    } catch (error) {
      state.error = error instanceof Error ? error.message : '签到失败，请稍后重试。';
      setText('#points-checkin-status', state.error);
      return false;
    } finally {
      checkingIn = false;
      render();
    }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-checkin]');
    if (!button || button.disabled) return;
    void checkIn();
  });

  window.addEventListener('auth-changed', () => { void refresh(); });
  window.FudanPoints = { refresh, checkIn, getState: () => ({ ...state }) };
  window.FudanPoints.ready = refresh();
  window.FudanPoints.ready.then(() => window.dispatchEvent(new Event('points-changed')));
})();
