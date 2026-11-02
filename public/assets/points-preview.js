'use strict';
(() => {
  const storageKey = 'fudan-course-atlas-points-preview-checkins-v2';
  const examDownloadsKey = 'fudan-course-atlas-points-preview-exam-file-unlocks-v2';
  const basePoints = 120;
  const dailyPoints = 5;
  const tiers = [
    { name: '同行者', threshold: 0 },
    { name: '共建伙伴', threshold: 50 },
    { name: '课程共建者', threshold: 150 },
  ];
  const $ = (selector) => document.querySelector(selector);

  function dateKey(date) {
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
  }

  function readCheckins() {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) || '[]');
      return Array.isArray(value)
        ? [...new Set(value.filter((day) => typeof day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(day)))].sort()
        : [];
    } catch {
      return [];
    }
  }

  function readExamDownloads() {
    try {
      const value = JSON.parse(localStorage.getItem(examDownloadsKey) || '[]');
      if (!Array.isArray(value)) return [];
      const unique = new Map();
      value.filter((entry) => entry && typeof entry.id === 'string').forEach((entry) => unique.set(entry.id, entry));
      return [...unique.values()];
    } catch {
      return [];
    }
  }

  function currentBalance() {
    return basePoints + readCheckins().length * dailyPoints - readExamDownloads().length;
  }

  function render() {
    const days = readCheckins();
    const today = dateKey(new Date());
    const checkedIn = days.includes(today);
    const downloads = readExamDownloads();
    const points = basePoints + days.length * dailyPoints - downloads.length;
    const currentTier = [...tiers].reverse().find((tier) => points >= tier.threshold) || tiers[0];
    const nextTier = tiers.find((tier) => tier.threshold > currentTier.threshold);
    const target = nextTier ? nextTier.threshold : currentTier.threshold;
    const remaining = nextTier ? target - points : 0;
    const percentage = target ? Math.min(100, (points / target) * 100) : 100;
    const last30Start = new Date();
    last30Start.setHours(0, 0, 0, 0);
    last30Start.setDate(last30Start.getDate() - 29);
    const recentCheckins = days.filter((day) => new Date(`${day}T00:00:00`).getTime() >= last30Start.getTime()).length;

    $('#points-balance-value').textContent = String(points);
    $('#points-recent-total').textContent = `+${45 + recentCheckins * dailyPoints}`;
    $('#points-next-label').textContent = nextTier ? `距离升级为「${nextTier.name}」` : '当前展示称号';
    $('#points-next-remaining').textContent = nextTier ? `还差 ${remaining} 分` : '已达成';
    $('#points-progress-fill').style.width = `${percentage}%`;
    $('.points-progress-track').setAttribute('aria-label', nextTier ? `距离下一等级还差${remaining}分` : '已达到课程共建者等级');
    $('#points-level-current').textContent = `当前：${currentTier.name}`;
    $('#points-progress-value').textContent = nextTier ? `${points} / ${target} 分` : `${points} 分`;
    $('#points-level-name').textContent = currentTier.name;
    document.querySelectorAll('[data-points-level]').forEach((row) => {
      row.classList.toggle('active-rank', row.dataset.pointsLevel === currentTier.name);
    });
    $('#points-checkin-status').textContent = checkedIn
      ? '今日已签到，+5 分已计入本地演示余额。'
      : '今天签到一次可得 +5 分；状态只保存在当前浏览器。';
    const button = $('[data-checkin]');
    button.disabled = checkedIn;
    button.textContent = checkedIn ? '今日已签到' : '立即签到 · +5 分';
    $('#points-checkin-activity').hidden = !checkedIn;
    const downloadActivity = $('#points-download-activity');
    if (downloadActivity) {
      downloadActivity.hidden = downloads.length === 0;
      $('#points-download-activity-detail').textContent = `独立文件解锁 · ${downloads.length} 份本地演示`;
      $('#points-download-activity-points').textContent = `−${downloads.length}`;
    }
  }

  function spendExamFile(fileId) {
    const downloads = readExamDownloads();
    const alreadyUnlocked = isExamFileUnlocked(fileId);
    if (alreadyUnlocked) return { ok: true, alreadyUnlocked: true, balance: currentBalance() };
    const balance = currentBalance();
    if (balance < 1) return { ok: false, balance };
    try {
      downloads.push({ id: fileId, time: new Date().toISOString() });
      localStorage.setItem(examDownloadsKey, JSON.stringify(downloads));
      render();
      return { ok: true, alreadyUnlocked: false, balance: balance - 1 };
    } catch {
      $('#points-checkin-status').textContent = '浏览器未能保存积分演示记录；本次文件访问没有记分。';
      return { ok: false, balance };
    }
  }

  function isExamFileUnlocked(fileId) {
    return readExamDownloads().some((entry) => typeof entry === 'object' && entry.id === fileId);
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-checkin]');
    if (!button || button.disabled) return;
    const days = readCheckins();
    const today = dateKey(new Date());
    if (days.includes(today)) {
      render();
      return;
    }
    try {
      localStorage.setItem(storageKey, JSON.stringify([...days, today]));
      render();
    } catch {
      $('#points-checkin-status').textContent = '浏览器未能保存签到状态；这次预览签到没有记分。';
    }
  });

  window.FudanPointsPreview = { currentBalance, isExamFileUnlocked, spendExamFile, render };
  render();
})();
