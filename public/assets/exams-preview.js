'use strict';
(() => {
  const pageSize = 24;
  const $ = (selector) => document.querySelector(selector);
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
  const formatSize = (bytes) => bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
  const allowedUrl = (value) => {
    try {
      const url = new URL(value);
      return url.protocol === 'https:' && url.hostname === 'github.com'
        && url.pathname.startsWith('/Annan-lyn/fudan-exam-paper/blob/main/')
        && !url.search && !url.hash && !url.username && !url.password;
    } catch { return false; }
  };

  let sets = [];
  let filtered = [];
  let shown = pageSize;

  function renderCards() {
    const query = ($('#exam-search')?.value || '').trim().toLowerCase();
    const category = $('#exam-category')?.value || 'all';
    filtered = sets.filter((item) => {
      const matchesCategory = category === 'all' || item.course.startsWith(`${category}-`);
      const haystack = [item.course, item.teacher, item.title, ...item.files.map((file) => file.name)].join(' ').toLowerCase();
      return matchesCategory && (!query || haystack.includes(query));
    });
    const visible = filtered.slice(0, shown);
    const results = $('#exam-results');
    if (results) results.innerHTML = visible.map((item) => `
      <article class="exam-card">
        <div class="exam-card-top"><span class="exam-course-tag">${escapeHtml(item.course)}</span><span class="exam-cost">↓ 1 积分 / 文件</span></div>
        <h2>${escapeHtml(item.title)}</h2>
        <p class="exam-teacher">${escapeHtml(item.teacher)} <span>·</span> ${item.fileCount} 个文件</p>
        <details class="exam-file-list">
          <summary>查看文件清单与单文件入口 · 首次解锁 1 积分</summary>
          <ul>${item.files.map((file) => {
            const available = Boolean(file.githubUrl);
            return `<li class="exam-file-entry">
              <div class="exam-file-meta"><span>${escapeHtml(file.name)}</span><small>${escapeHtml(file.extension.toUpperCase())} · ${formatSize(file.sizeBytes)}</small></div>
              <div class="exam-file-action"><button class="exam-open-file" data-exam-file="${escapeHtml(file.id)}" type="button" ${available ? '' : 'disabled'}>${available ? '本站解锁 · 1 积分' : '暂无单文件链接'}</button><small class="exam-file-status" aria-live="polite" data-exam-status="${escapeHtml(file.id)}">${available ? '' : '未能在目标仓库里唯一匹配到这份文件，未扣分。'}</small></div>
            </li>`;
          }).join('')}</ul>
        </details>
        <div class="exam-card-bottom"><small>${item.existingAsset ? `与站内已有文件 ${escapeHtml(item.existingAsset)} 内容一致。` : '首次解锁只扣 1 分；同一账户重复打开这份文件免费，同套其他文件需分别解锁。'}</small></div>
      </article>`).join('') || '<div class="exam-empty">没有找到匹配的试卷，试试课程名或教师名。</div>';
    const count = $('#exam-results-count');
    if (count) count.textContent = `${filtered.length} 条`;
    const loadMore = $('#exam-load-more');
    if (loadMore) {
      loadMore.hidden = visible.length >= filtered.length;
      loadMore.textContent = `再显示 ${Math.min(pageSize, filtered.length - visible.length)} 条`;
    }
  }

  async function unlockFile(button, status) {
    const fileId = button?.dataset?.examFile;
    if (!fileId || !status || button.disabled) return false;
    status.replaceChildren();
    status.textContent = '正在向服务端确认单文件解锁…';
    button.disabled = true;
    try {
      const response = await fetch(`/api/exams/${encodeURIComponent(fileId)}/unlock`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: '{}',
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          status.textContent = '请先登录再解锁。';
          const login = document.createElement('a');
          login.href = '/signin-with-chatgpt?return_to=%2Findex.html%23exams';
          login.target = '_top';
          login.textContent = '登录 ↗';
          status.append(' ', login);
          const loginNotice = $('[data-points-login]');
          if (loginNotice) loginNotice.hidden = false;
        } else if (response.status === 402) {
          status.textContent = `积分不足；当前余额 ${Number(data.balance) || 0} 分。每日签到可得 5 分。`;
        } else if (response.status === 404) {
          status.textContent = '该文件没有可用的单文件链接，本次没有扣分。';
        } else {
          status.textContent = '服务暂不可用，本次没有确认解锁或扣分，请稍后重试。';
        }
        return false;
      }
      if (!allowedUrl(data.url)) throw new Error('服务返回了无效的文件地址。');
      button.textContent = '已解锁 · 再次打开免费';
      status.textContent = data.charged ? `已扣 1 分，余额 ${data.balance} 分；只解锁这一份文件。` : `这份文件已解锁，本次免费打开；余额 ${data.balance} 分。`;
      const link = document.createElement('a');
      link.href = data.url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = '打开这一份 GitHub 文件 ↗';
      status.append(' ', link);
      await window.FudanPoints?.refresh?.();
      return true;
    } catch {
      status.textContent = '服务暂不可用，暂时无法确认文件解锁。请稍后重试。';
      return false;
    } finally {
      button.disabled = false;
    }
  }

  async function init() {
    try {
      const response = await fetch('data/exams-preview.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      sets = data.sets || [];
      const setTotal = $('#exam-set-total');
      const fileTotal = $('#exam-file-total');
      const subjectTotal = $('#exam-subject-total');
      if (setTotal) setTotal.textContent = String(data.setCount || sets.length);
      if (fileTotal) fileTotal.textContent = String(data.fileCount || 0);
      if (subjectTotal) subjectTotal.textContent = String(data.subjectCount || 0);
      const categorySelect = $('#exam-category');
      const categories = [...new Set(sets.map((item) => item.course.split('-', 1)[0]))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
      categorySelect?.insertAdjacentHTML('beforeend', categories.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join(''));
      $('#exam-search')?.addEventListener('input', () => { shown = pageSize; renderCards(); });
      categorySelect?.addEventListener('change', () => { shown = pageSize; renderCards(); });
      $('#exam-load-more')?.addEventListener('click', () => { shown += pageSize; renderCards(); });
      document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-exam-file]');
        if (!button || button.disabled) return;
        const status = document.querySelector(`[data-exam-status="${button.dataset.examFile}"]`);
        void unlockFile(button, status);
      });
      renderCards();
    } catch (error) {
      const results = $('#exam-results');
      if (results) results.innerHTML = '<div class="exam-empty">试卷目录暂时无法加载，请稍后刷新。</div>';
      console.error('Could not initialize exam index:', error);
    }
  }

  const ready = init();
  window.ExamPreview = { init, render: renderCards, unlockFile, ready };
})();
