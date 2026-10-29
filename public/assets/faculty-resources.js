'use strict';

(() => {
  const RESOURCE_TYPES = {
    curriculum: '培养方案',
    'student-handbook': '学生手册',
    'course-catalog': '课程目录',
    'course-story': '课程体验报道',
    'teaching-study': '教学研究',
    'training-system': '培养体系报道',
    'student-interview': '学生访谈'
  };
  const SOURCE_TYPES = {
    'official-program': '官方培养方案',
    'official-directory': '官方目录',
    'official-course-list': '官方课程列表',
    'official-feature': '校方专题报道',
    'official-student-interview': '校方学生访谈',
    'academic-study': '学术教学研究',
    'media-report': '媒体报道'
  };
  const FACULTIES = { engineering: '工科', medicine: '医科' };
  const state = { records: [], status: 'loading' };
  const list = () => document.querySelector('#faculty-resource-list');
  const selectedFilters = () => ({
    faculty: document.querySelector('#faculty-resource-faculty')?.value || 'all',
    type: document.querySelector('#faculty-resource-type')?.value || 'all'
  });

  function make(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = String(text);
    return element;
  }

  function message(container, className, text) {
    container.replaceChildren(make('p', className, text));
  }

  function validRecord(record) {
    if (!record || typeof record !== 'object') return false;
    if (!['engineering', 'medicine'].includes(record.faculty)) return false;
    if (!record.id || !record.title || !record.source_label) return false;
    if (!record.source_type || !record.resource_type) return false;
    if (typeof record.summary !== 'string' || typeof record.scope_note !== 'string') return false;
    try {
      const url = new URL(record.url);
      return url.protocol === 'https:' && !url.username && !url.password;
    } catch {
      return false;
    }
  }

  function card(record) {
    const article = make('article', 'faculty-resource-card');
    const header = make('div', 'faculty-resource-card-header');
    const category = make('span', 'resource-chip', RESOURCE_TYPES[record.resource_type] || '资料');
    const faculty = make('span', 'resource-faculty', FACULTIES[record.faculty] || '院系');
    header.append(category, faculty);
    article.append(header);

    article.append(make('p', 'resource-department', record.department || '院系未注明'));
    article.append(make('h2', 'resource-title', record.title));
    article.append(make('p', 'resource-summary', record.summary));

    const meta = make('dl', 'resource-meta');
    const details = [
      ['学年/学期', record.academic_year || '原文未标注'],
      ['来源类型', SOURCE_TYPES[record.source_type] || record.source_type],
      ['来源', record.source_label],
      ['发布/更新', record.publication_date || '原文未标注'],
      ['核验状态', record.verification_status || '待进一步核对'],
      ['转载状态', record.reuse_status || '仅提供来源链接']
    ];
    for (const [label, value] of details) {
      const row = make('div', 'resource-meta-row');
      row.append(make('dt', '', label), make('dd', '', value));
      meta.append(row);
    }
    article.append(meta);

    const scope = make('p', 'resource-scope-note', record.scope_note);
    article.append(scope);
    if (Array.isArray(record.course_codes) && record.course_codes.length) {
      article.append(make('p', 'resource-course-codes', `课程代码：${record.course_codes.join('、')}`));
    }

    const link = make('a', 'resource-link', '打开原始来源 ↗');
    link.href = record.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    article.append(link);
    return article;
  }

  function render(container, filters = {}) {
    if (!container) return;
    const count = document.querySelector('#faculty-resource-count');
    if (state.status === 'loading') {
      if (count) count.textContent = '正在读取来源索引…';
      message(container, 'resource-state', '正在读取院系资料…');
      return;
    }
    if (state.status === 'error') {
      if (count) count.textContent = '资料索引暂不可用';
      message(container, 'resource-state resource-error', '院系资料暂时无法载入，请稍后重试。');
      return;
    }

    const faculty = ['engineering', 'medicine'].includes(filters.faculty) ? filters.faculty : 'all';
    const type = Object.hasOwn(RESOURCE_TYPES, filters.type) ? filters.type : 'all';
    const records = state.records.filter(record =>
      (faculty === 'all' || record.faculty === faculty) &&
      (type === 'all' || record.resource_type === type)
    );
    if (count) count.textContent = `当前显示 ${records.length} 条资料 · 索引共 ${state.records.length} 条`;
    if (!records.length) {
      message(container, 'resource-state', '没有符合条件的资料。可以切换筛选条件，或选择“全部院系 / 全部类型”。');
      return;
    }
    container.replaceChildren(...records.map(card));
  }

  async function init() {
    state.status = 'loading';
    render(list());
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch('data/faculty-resources.json', { cache: 'no-cache', signal: controller.signal });
      if (!response.ok) throw new Error(`resource index returned ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data)) throw new Error('resource index is not an array');
      state.records = data.filter(validRecord);
      state.status = 'ready';
    } catch (error) {
      console.error('Could not load faculty resources:', error);
      state.status = 'error';
    } finally {
      clearTimeout(timeout);
    }
    render(list(), selectedFilters());

    for (const selector of ['#faculty-resource-faculty', '#faculty-resource-type']) {
      document.querySelector(selector)?.addEventListener('change', () => render(list(), selectedFilters()));
    }
  }

  window.FacultyResources = { init, render };
})();
