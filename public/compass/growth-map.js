const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

export function branchingMap({ title, subtitle, branches, className = '' }) {
  return `<section class="growth-tree ${className}" aria-label="${escape(title)}">
    <div class="growth-root"><h2>${escape(title)}</h2>${subtitle ? `<p>${escape(subtitle)}</p>` : ''}</div>
    <ul class="growth-branches">${branches.map(({ label, heading, leaves }) => `<li class="growth-branch">
      <div class="growth-stage">${label ? `<small>${escape(label)}</small>` : ''}<h3>${escape(heading)}</h3></div>
      <ul class="growth-leaves">${leaves.map(({ heading, content }) => `<li class="growth-leaf">
        <h4>${escape(heading)}</h4>${content}
      </li>`).join('')}</ul>
    </li>`).join('')}</ul>
  </section>`;
}

export function growthDiagram(goals, active, stages) {
  const goal = goals[active];
  const outcomes = ['学习笔记与复盘', '可运行代码与实验记录', '作品集与下一阶段目标'];
  const branches = stages.map(([heading, label, task, words], index) => ({
    label,
    heading,
    leaves: [
      { heading: '行动建议', content: `<p>${escape(task)}</p>` },
      { heading: '关联课程', content: `<div class="growth-course-links">${words.map(word =>
        `<button type="button" data-query="${escape(word)}">${escape(word)}</button>`).join('')}</div>` },
      { heading: '阶段成果', content: `<p>${outcomes[index]}</p>` },
    ],
  }));
  const choices = `<div class="filters growth-intro" role="group" aria-label="选择成长方向">${Object.entries(goals).map(([id, option]) =>
    `<button type="button" class="button ${active === id ? 'primary' : 'ghost'}" aria-pressed="${active === id}" data-path-goal="${escape(id)}">${escape(option.label)}</button>`).join('')}</div>`;
  return choices + branchingMap({ title: goal.label, subtitle: goal.outcome, branches });
}
