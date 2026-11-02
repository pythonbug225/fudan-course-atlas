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

  let sets = [];
  let filtered = [];
  let shown = pageSize;

  function renderCards() {
    const query = $('#exam-search').value.trim().toLowerCase();
    const category = $('#exam-category').value;
    filtered = sets.filter((item) => {
      const matchesCategory = category === 'all' || item.course.startsWith(`${category}-`);
      const haystack = [item.course, item.teacher, item.title, ...item.files.map((file) => file.name)].join(' ').toLowerCase();
      return matchesCategory && (!query || haystack.includes(query));
    });
    const visible = filtered.slice(0, shown);
    $('#exam-results').innerHTML = visible.map((item) => `
      <article class="exam-card">
        <div class="exam-card-top"><span class="exam-course-tag">${escapeHtml(item.course)}</span><span class="exam-cost">↓ 1 积分 / 文件</span></div>
        <h2>${escapeHtml(item.title)}</h2>
        <p class="exam-teacher">${escapeHtml(item.teacher)} <span>·</span> ${item.fileCount} 个文件</p>
        <details class="exam-file-list">
          <summary>查看文件清单与单文件入口 · 每份 1 积分</summary>
          <ul>${item.files.map((file) => {
            const fileId = file.id;
            const available = Boolean(file.githubUrl);
            const unlocked = available && window.FudanPointsPreview?.isExamFileUnlocked(fileId);
            const buttonLabel = !available ? '暂无单文件链接' : unlocked ? '已解锁 · 再次打开免费' : '打开这一份 · 1 积分';
            return `<li class="exam-file-entry">
              <div class="exam-file-meta"><span>${escapeHtml(file.name)}</span><small>${escapeHtml(file.extension.toUpperCase())} · ${formatSize(file.sizeBytes)}</small></div>
              <div class="exam-file-action"><button class="exam-open-file" data-exam-file="${escapeHtml(fileId)}" data-exam-url="${escapeHtml(file.githubUrl || '')}" type="button" ${available ? '' : 'disabled'}>${buttonLabel}</button><small class="exam-file-status" aria-live="polite" data-exam-status="${escapeHtml(fileId)}">${available ? '' : '未能在目标仓库里唯一匹配到这份文件，未扣分。'}</small></div>
            </li>`;
          }).join('')}</ul>
        </details>
        <div class="exam-card-bottom"><small>${item.existingAsset ? `与站内已有文件 ${escapeHtml(item.existingAsset)} 内容一致。` : '按钮只打开 GitHub 中匹配到的单份文件；同套题的其他文件需分别解锁。'}</small></div>
      </article>`).join('') || '<div class="exam-empty">没有找到匹配的试卷，试试课程名或教师名。</div>';
    $('#exam-results-count').textContent = `${filtered.length} 条`;
    $('#exam-load-more').hidden = visible.length >= filtered.length;
    $('#exam-load-more').textContent = `再显示 ${Math.min(pageSize, filtered.length - visible.length)} 条`;
  }

  async function init() {
    try {
      const response = await fetch('data/exams-preview.json', { cache: 'no-cache' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      sets = data.sets || [];
      $('#exam-set-total').textContent = String(data.setCount || sets.length);
      $('#exam-file-total').textContent = String(data.fileCount || 0);
      $('#exam-subject-total').textContent = String(data.subjectCount || 0);
      const categories = [...new Set(sets.map((item) => item.course.split('-', 1)[0]))].sort((a, b) => a.localeCompare(b, 'zh-CN'));
      $('#exam-category').insertAdjacentHTML('beforeend', categories.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join(''));
      $('#exam-search').addEventListener('input', () => { shown = pageSize; renderCards(); });
      $('#exam-category').addEventListener('change', () => { shown = pageSize; renderCards(); });
      $('#exam-load-more').addEventListener('click', () => { shown += pageSize; renderCards(); });
      document.addEventListener('click', (event) => {
        const button = event.target.closest('[data-exam-file]');
        if (!button) return;
        const fileId = button.dataset.examFile;
        const status = document.querySelector(`[data-exam-status="${fileId}"]`);
        const url = button.dataset.examUrl;
        status.replaceChildren();
        if (!url.startsWith('https://github.com/Annan-lyn/fudan-exam-paper/blob/main/')) {
          status.textContent = '没有可验证的 GitHub 单文件链接，本次没有扣分。';
          return;
        }
        const result = window.FudanPointsPreview?.spendExamFile(fileId);
        if (!result) {
          status.textContent = '积分演示尚未加载，请刷新页面后再试。';
        } else if (!result.ok) {
          status.textContent = '积分不足。每日签到可得 5 分；浏览课评和大纲仍然免费。';
        } else if (result.alreadyUnlocked) {
          status.textContent = `这份文件已解锁，可再次打开而不扣分。当前演示余额 ${result.balance} 分。`;
          button.textContent = '已解锁 · 再次打开免费';
          const link = document.createElement('a');
          link.href = url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = '若未自动打开，点击此处';
          status.append(' ', link);
        } else {
          status.textContent = `已扣 1 分，余额 ${result.balance} 分；只解锁这一个文件。`;
          button.textContent = '已解锁 · 再次打开免费';
          const link = document.createElement('a');
          link.href = url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = '若未自动打开，点击此处';
          status.append(' ', link);
        }
        if (result?.ok) window.open(url, '_blank', 'noopener,noreferrer');
      });
      renderCards();
    } catch (error) {
      $('#exam-results').innerHTML = '<div class="exam-empty">试卷目录预览未能加载，请刷新本地预览。</div>';
      console.error('Could not initialize exam preview:', error);
    }
  }

  window.ExamPreview = { init, render: renderCards };
  init();
})();
