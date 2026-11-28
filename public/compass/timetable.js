import { creditTotal, overlap, parseSchedule } from './engine.js';

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

function weeklySlots(parsed, week) {
  const unique = new Map();
  for (const slot of parsed.slots) {
    if (!slot.weeks.includes(week)) continue;
    const key = `${slot.day}-${slot.start}-${slot.end}`;
    if (!unique.has(key)) unique.set(key, slot);
  }
  return [...unique.values()];
}

export function weekWithClasses(items, preferred) {
  const weeks = new Set(items.flatMap(item =>
    parseSchedule(item.section.schedule).slots.flatMap(slot => slot.weeks)));
  if (!weeks.size || weeks.has(preferred)) return preferred;
  return Math.min(...weeks);
}

export function availableSections(item, items, sections, preferences) {
  const others = items.filter(other => other !== item);
  const otherSlots = others
    .filter(other => other.section.term === item.section.term)
    .flatMap(other => parseSchedule(other.section.schedule).slots);
  const otherCredits = creditTotal(others);
  const currentCredits = creditTotal(items);

  return (sections ?? [])
    .filter(section => section.term === item.section.term && section.id !== item.section.id)
    .map(section => {
      const parsed = parseSchedule(section.schedule);
      const nextCredits = otherCredits + Number(section.credits);
      let reason = '';
      if (!parsed.complete) reason = '上课时间不完整';
      else if (parsed.slots.some(slot => otherSlots.some(other => overlap(slot, other)))) reason = '与候选课表冲突';
      else if (preferences.freeWednesday && parsed.slots.some(slot =>
        slot.day === 3 && slot.start <= 10 && slot.end >= 6)) reason = '占用周三下午';
      else if (nextCredits > Number(preferences.maxCredits) + 0.001 && nextCredits > currentCredits + 0.001) {
        reason = '超过方案学分上限';
      }
      return { section, parsed, reason };
    });
}

// Give overlapping classes separate lanes so every card can still be opened.
function arrangeCards(cards) {
  for (const day of days.keys()) {
    const column = cards.filter(card => card.day === day + 1).sort((a, b) => a.start - b.start || a.end - b.end);
    let group = [];
    let occupied = [];
    let last = 0;
    const finish = () => group.forEach(card => { card.lanes = occupied.length; });
    for (const card of column) {
      if (card.start > last) {
        finish();
        group = [];
        occupied = [];
      }
      let lane = occupied.findIndex(end => end < card.start);
      if (lane < 0) lane = occupied.length;
      occupied[lane] = card.end;
      card.lane = lane;
      group.push(card);
      last = Math.max(last, card.end);
    }
    finish();
  }
  return cards;
}

export function renderTimetable({ items, week, slot, term, conflictCount, canUndo, busy }) {
  const prepared = items.map(item => ({ item, parsed: parseSchedule(item.section.schedule) }));
  const unknown = prepared.filter(item => !item.parsed.complete).length;
  const weeks = Math.max(20, ...prepared.flatMap(item => item.parsed.slots.flatMap(slot => slot.weeks)));
  const periods = Math.max(14, ...prepared.flatMap(item => item.parsed.slots.map(slot => slot.end)));
  const cards = arrangeCards(prepared.flatMap(({ item, parsed }, index) =>
    weeklySlots(parsed, week).map(time => ({ ...time, item, color: index % 5 }))));
  const disabled = busy ? 'disabled' : '';
  const grid = ['节次', ...days].map((label, index) =>
    `<span class="tt-heading" style="grid-area:1/${index + 1}">${label}</span>`);
  for (let period = 1; period <= periods; period++) {
    grid.push(`<span class="tt-period" style="grid-area:${period + 1}/1">${period}</span>`);
    grid.push(...days.map((_, index) =>
      `<span class="tt-cell" style="grid-area:${period + 1}/${index + 2}"></span>`));
  }

  return `<section class="panel timetable" id="weekly-timetable" tabindex="-1" aria-labelledby="timetable-title">
    <header class="tt-header">
      <div><p class="tt-term">${escape(term)}</p><h2 id="timetable-title">候选课表</h2></div>
      <div class="tt-actions">
        <div class="tt-toggle" role="group" aria-label="选择方案">
          ${['A', 'B'].map(name => `<button type="button" data-tt-plan="${name}" aria-pressed="${name === slot}" ${disabled}>方案 ${name}</button>`).join('')}
        </div>
        <button type="button" class="button ghost tt-undo" data-tt-undo ${!canUndo || busy ? 'disabled' : ''}>撤销编辑</button>
      </div>
    </header>
    <div class="tt-toolbar">
      <div class="tt-summary" aria-live="polite">
        <strong>${items.length} 门 · ${creditTotal(items)} 学分</strong>
        <span class="tt-status ${conflictCount ? 'tt-warning' : ''}">${conflictCount ? `${conflictCount} 组时间冲突` : '无已知冲突'}</span>
        ${unknown ? `<span class="tt-status tt-warning">${unknown} 门时间待核对</span>` : ''}
      </div>
      <div class="tt-weeks">
        <button type="button" data-tt-week="${week - 1}" aria-label="上一周" ${week <= 1 ? 'disabled' : ''}>‹</button>
        <select data-tt-week-select aria-label="查看教学周">
          ${Array.from({ length: weeks }, (_, index) => `<option value="${index + 1}" ${week === index + 1 ? 'selected' : ''}>第 ${index + 1} 周</option>`).join('')}
        </select>
        <button type="button" data-tt-week="${week + 1}" aria-label="下一周" ${week >= weeks ? 'disabled' : ''}>›</button>
      </div>
    </div>
    <p class="tt-help">${busy ? '智能体正在规划，完成后可以编辑。' : '拖到高亮时间格换班，或拖到下方移除区。也可以点课程卡片操作。'}</p>
    <div class="tt-scroll" tabindex="0" aria-label="周课表，可横向滚动">
      <div class="tt-grid" style="--tt-periods:${periods}">
        ${grid.join('')}
        ${cards.map(({ item, day, start, end, location, color, lane, lanes }) => `<button type="button"
          class="tt-card tt-color-${color}" data-tt-edit="${escape(item.course.id)}" draggable="${!busy}"
          style="grid-area:${start + 1}/${day + 1}/${end + 2}/span 1;--tt-left:${100 * lane / lanes}%;--tt-width:${100 / lanes}%"
          title="${escape(item.course.name)} · ${days[day - 1]}第 ${start}–${end} 节" ${disabled}>
          <strong>${escape(item.course.name)}</strong><small>${escape(location || item.section.teachers.join('、'))}</small>
        </button>`).join('')}
        ${!cards.length ? `<div class="tt-empty">${items.length ? '这一周没有可显示的节次' : '生成方案或从课程详情加入教学班'}</div>` : ''}
      </div>
    </div>
    <div class="tt-footer">
      <div class="tt-drop-area">
        <div class="tt-drop" data-tt-trash><span aria-hidden="true">×</span>拖到这里移出候选</div>
        <button type="button" class="button ghost tt-clear" data-tt-clear ${!items.length || busy ? 'disabled' : ''}>清空候选</button>
      </div>
      <details class="tt-course-list">
        <summary>全部候选课程（${items.length}）</summary>
        <ul>${items.map(({ course, section }) => `<li><div><strong>${escape(course.name)}</strong><small>${escape(section.code)} · ${section.credits} 学分</small></div><button type="button" class="button ghost" data-tt-edit="${escape(course.id)}" ${disabled}>换班或移除</button></li>`).join('')}</ul>
      </details>
    </div>
  </section>`;
}

export function bindTimetable(board, actions) {
  if (!board) return;
  let dragged = '';
  let targets = new Map();
  const clear = () => {
    dragged = '';
    targets.clear();
    board.classList.remove('tt-dragging');
    board.querySelectorAll('.tt-target').forEach(target => target.remove());
    board.querySelector('.tt-drop-active')?.classList.remove('tt-drop-active');
  };

  board.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || button.disabled) return;
    if (button.hasAttribute('data-tt-undo')) actions.undo();
    else if (button.hasAttribute('data-tt-clear')) actions.clear();
    else if (button.dataset.ttEdit) actions.edit(button.dataset.ttEdit);
    else if (button.dataset.ttWeek) actions.week(Number(button.dataset.ttWeek));
    else if (button.dataset.ttPlan) actions.plan(button.dataset.ttPlan);
  });
  board.querySelector('[data-tt-week-select]').onchange = event => actions.week(Number(event.target.value));
  board.addEventListener('dragstart', event => {
    const card = event.target.closest('[data-tt-edit][draggable="true"]');
    if (!card || !event.dataTransfer) return;
    clear();
    dragged = card.dataset.ttEdit;
    event.dataTransfer.setData('text/plain', dragged);
    event.dataTransfer.effectAllowed = 'move';
    for (const option of actions.choices(dragged)) {
      if (option.reason) continue;
      for (const time of weeklySlots(option.parsed, actions.currentWeek)) {
        const key = `${time.day}-${time.start}`;
        if (!targets.has(key)) targets.set(key, new Set());
        targets.get(key).add(option.section.id);
      }
    }
    const grid = board.querySelector('.tt-grid');
    for (const [key] of targets) {
      const [day, period] = key.split('-').map(Number);
      const marker = document.createElement('span');
      marker.className = 'tt-target';
      marker.dataset.ttTarget = key;
      marker.setAttribute('aria-hidden', 'true');
      marker.style.gridArea = `${period + 1}/${day + 1}`;
      grid.append(marker);
    }
    board.classList.add('tt-dragging');
  });
  board.addEventListener('dragover', event => {
    if (!dragged) return;
    const target = event.target.closest('[data-tt-target], [data-tt-trash]');
    board.querySelector('.tt-drop-active')?.classList.remove('tt-drop-active');
    if (!target) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    target.classList.add('tt-drop-active');
  });
  board.addEventListener('dragleave', event => {
    event.target.closest('.tt-drop-active')?.classList.remove('tt-drop-active');
  });
  board.addEventListener('drop', event => {
    if (!dragged) return;
    const target = event.target.closest('[data-tt-target], [data-tt-trash]');
    if (!target) return;
    event.preventDefault();
    const id = dragged;
    const choices = [...(targets.get(target.dataset.ttTarget) ?? [])];
    clear();
    if (target.hasAttribute('data-tt-trash')) actions.remove(id);
    else if (choices.length === 1) actions.replace(id, choices[0]);
    else if (choices.length > 1) actions.edit(id, choices);
  });
  board.addEventListener('dragend', clear);
}
