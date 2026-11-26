const element = id => document.getElementById(id);
const scope = element('scope');
const lines = element('lines');
const graph = element('graph');
const columns = element('columns');
const svg = element('links');
const query = new URLSearchParams(location.search);
const selectors = ['year', 'category', 'department', 'major', 'plan'];
const courseTypes = {
  syllabus_prerequisite: ['大纲明确先修', '#246082', ''],
  official_preparation: ['方案明确预修', '#374989', '10 3'],
  official_sequence: ['方案文字指定顺序', '#5c498b', '8 3 2 3'],
  recommended_preparation: ['知识衔接建议', '#955c2e', '6 4'],
  term_order: ['方案排课先后', '#987026', '3 4'],
  content: ['课程内容联系', '#807079', '1 4'],
};
const sourceKinds = {system: '教务方案', annual: '年度汇编', advice: '修读建议'};
const disciplineOrder = ['文', '理', '工', '医', '跨类'];
let plans = [], departmentCategories = {}, detail, courses = new Map(), focusId = '', request = 0, drawFrame = 0;
const byName = new Intl.Collator('zh-Hans-CN', {numeric: true});
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function setOptions(select, values, preferred) {
  select.replaceChildren(...values.map(([value, label]) => new Option(label, value)));
  if (values.some(([value]) => value === preferred)) select.value = preferred;
}
function filterPlans(changed = '', wanted) {
  let subset = plans.flatMap(p => [...new Set([p.department, ...(p.relatedDepartments || [])])].map(department => ({
    ...p, department, category: departmentCategories[department] || p.category, sourceDepartment: p.department,
  })));
  let reset = false;
  for (const key of selectors) {
    const select = element(key);
    const field = key === 'plan' ? 'id' : key;
    const choices = new Map(subset.map(p => [String(p[field]), key === 'plan' ? (sourceKinds[p.sourceKind] || '教务方案') + ' · ' + p.title + ' · ' + p.id : String(p[field])]));
    const values = [...choices].sort(([a, an], [b, bn]) => {
      if (key === 'year') return Number(b) - Number(a);
      if (key === 'category') return disciplineOrder.indexOf(a) - disciplineOrder.indexOf(b);
      return byName.compare(an, bn);
    });
    const preference = String(wanted?.[field] ?? (reset ? '' : select.value));
    const systemFirst = subset.find(p => !p.sourceKind || p.sourceKind === 'system');
    setOptions(select, values, values.some(([v]) => v === preference) ? preference : key === 'plan' ? String(systemFirst?.id ?? '') : '');
    const chips = element(key + '-options');
    if (chips && (key === 'category' || key === 'department')) {
      chips.replaceChildren(...values.map(([value, label]) => {
        const choice = node('button', label);
        choice.type = 'button';
        choice.setAttribute('aria-pressed', String(select.value === value));
        choice.onclick = () => { select.value = value; filterPlans(key); };
        return choice;
      }));
    }
    subset = subset.filter(p => String(p[field]) === select.value);
    if (key === changed) reset = true;
  }
  if (subset.length) loadPlan(subset[0]);
}
async function json(path) {
  const result = await fetch(path);
  if (!result.ok) throw new Error('HTTP ' + result.status);
  return result.json();
}
function syncAddress(plan) {
  const url = new URL(location.href);
  url.searchParams.set('year', plan.year);
  url.searchParams.set('plan', plan.id);
  url.searchParams.set('department', element('department').value);
  history.replaceState(null, '', url);
  if (parent !== window && location.ancestorOrigins?.[0] === location.origin && parent.location.pathname === '/compass') {
    const outer = new URL(parent.location.href);
    outer.searchParams.set('cohort', plan.year);
    outer.searchParams.set('plan', plan.id);
    outer.searchParams.set('department', element('department').value);
    parent.history.replaceState(null, '', outer);
  }
}
function fail(text, retry) {
  element('status').textContent = text;
  element('retry').hidden = false;
  element('retry').onclick = retry;
}
async function loadPlan(plan) {
  const serial = ++request;
  element('map').hidden = true;
  element('retry').hidden = true;
  element('status').textContent = '正在读取' + plan.title + '…';
  focusId = '';
  try {
    const next = await json('data/cohorts/' + encodeURIComponent(plan.year) + '/' + encodeURIComponent(plan.id) + '.json');
    if (serial !== request) return;
    detail = next;
    courses = new Map(next.courses.map(c => [String(c.id), c]));
    const sections = new Map((detail.syllabusReferences || []).map(ref => [sectionKey(ref), sectionLabel(ref)]));
    setOptions(element('syllabus'), [['', '请选择教学班'], ...sections], '');
    element('syllabus-label').hidden = !sections.size;
    if (scope.value === 'core' && !next.courses.some(inScope)) scope.value = 'all';
    element('title').textContent = plan.title;
    element('summary').textContent = [plan.year + ' 级', plan.sourceDepartment, sourceKinds[plan.sourceKind] || '教务方案', next.studentType || plan.studentType, courses.size + ' 门课程', next.edges.length + ' 条关系'].filter(Boolean).join(' · ');
    element('search').value = '';
    element('course-options').replaceChildren(...[...courses.values()].filter(c => !c.publicReference).map(c => new Option(c.name, c.code || c.id)));
    const links = [];
    for (const [label, url] of [[plan.sourceKind === 'annual' || plan.sourceKind === 'advice' ? '汇编原文' : '教务原文', next.sourceUrl], ['方案原件', next.wordUrl || next.originalUrl], ['逐条依据', next.graphUrl]]) {
      if (!url || !/^https:\/\//i.test(url)) continue;
      const a = node('a', label);
      a.href = url;
      a.target = '_blank';
      a.rel = 'noopener';
      links.push(a);
    }
    element('sources').replaceChildren(...links);
    const companions = element('companions');
    companions.replaceChildren();
    const related = (next.relatedSections || []).filter(s => String(s.id) !== String(plan.id));
    if (related.length) companions.append(node('strong', '配套方案与修读建议'));
    for (const section of related) {
      const link = node('a', section.title);
      const url = new URL(location.href);
      url.searchParams.set('plan', section.id);
      url.searchParams.set('year', plan.year);
      url.searchParams.set('department', element('department').value);
      link.href = url.href;
      companions.append(link);
    }
    element('guide').replaceChildren(...(next.guide || []).map(text => node('li', text)));
    element('reading').hidden = !next.guide?.length;
    element('status').textContent = '';
    element('map').hidden = false;
    syncAddress(plan);
    renderGraph();
    renderPanel();
  } catch (error) {
    if (serial === request) fail(plan.title + '载入失败（' + error.message + '）。', () => loadPlan(plan));
  }
}
function termNumbers(course) {
  return [...new Set((course.terms || []).map(Number).filter(n => Number.isInteger(n) && n > 0))].sort((a, b) => a - b);
}
function termText(course) {
  const terms = termNumbers(course);
  const labels = terms.map(t => '第' + t + '学期');
  labels.push(...(course.termsToken || []));
  return labels.join('、') || '学期未指定';
}
function courseCaption(course) {
  return [course.code || '', course.credits != null && course.credits !== '' ? course.credits + '学分' : '', course.required === true ? '必修' : ''].filter(Boolean).join(' · ');
}
function inScope(course) {
  return !course.publicReference && (scope.value === 'all' || (scope.value === 'required' ? course.required === true : course.core));
}
function typeOf(edge) {
  return courseTypes[edge.type] || [edge.type, '#626666', '4 4'];
}
function sectionKey(ref) {
  return JSON.stringify([ref.term, ref.section_code, ref.lesson_id]);
}
function sectionLabel(ref) {
  return [ref.term, ref.section_code || ref.lesson_id, Array.isArray(ref.teachers) ? ref.teachers.join('、') : ref.teachers].filter(Boolean).join(' · ');
}
function currentEdges() {
  const selected = element('syllabus').value;
  const references = selected ? (detail.syllabusReferences || []).filter(r => sectionKey(r) === selected).map(r => ({...r, type:'syllabus_prerequisite', reference: true})) : [];
  return [...detail.edges, ...references];
}
function renderGraph() {
  const all = [...courses.values()];
  const visible = all.filter(inScope);
  const groups = new Map();
  for (const course of visible) {
    const term = termNumbers(course)[0] || 0;
    if (!groups.has(term)) groups.set(term, []);
    groups.get(term).push(course);
  }
  const termColumns = [];
  const degrees = new Map();
  for (const edge of currentEdges()) {
    for (const id of [String(edge.from), String(edge.to)]) degrees.set(id, 1 + (degrees.get(id) || 0));
  }
  const sorted = [...groups].sort(([a], [b]) => (a || Infinity) - (b || Infinity));
  for (const [term, group] of sorted) {
    const col = node('section', null, 'term');
    col.append(node('h3', (term ? '第' + term + '学期' : '学期未指定') + ' · ' + group.length));
    for (const course of group.sort((a, b) => byName.compare(a.name, b.name))) {
      const card = node('article', null, 'course');
      card.dataset.id = course.id;
      if (String(course.id) === focusId) card.classList.add('current');
      const title = node(course.cardId ? 'a' : 'strong', course.name);
      if (course.cardId) {
        title.href = '/#course=' + encodeURIComponent(course.cardId);
        title.target = '_top';
      }
      const degree = degrees.get(String(course.id)) || 0;
      const button = node('button', degree ? '关系 · ' + degree : '课程信息');
      button.type = 'button';
      button.setAttribute('aria-label', course.name + '的课程关系');
      button.setAttribute('aria-pressed', String(String(course.id) === focusId));
      card.title = termText(course);
      card.append(title, node('small', courseCaption(course)));
      if (termNumbers(course).length > 1 || course.termsToken?.length) card.append(node('small', termText(course)));
      card.append(button);
      col.append(card);
    }
    termColumns.push(col);
  }
  let empty = '此范围尚无可定位的课程，可切换至方案全部专业课程。';
  if (!all.length) empty = '本节原页尚无可逐行定位的课程。请查看上方方案原件及下方导读。';
  else if (scope.value === 'required') empty = '现有记录尚未确认无条件必修的课程。请选择其他范围，或查阅方案原件中的要求。';
  columns.replaceChildren(...(termColumns.length ? termColumns : [node('p', empty)]));
  const visibleIds = new Set(visible.map(c => String(c.id)));
  const edges = currentEdges().filter(e => visibleIds.has(String(e.from)) && visibleIds.has(String(e.to)) && (lines.value !== 'syllabus' || e.type === 'syllabus_prerequisite'));
  const kinds = [...new Set(edges.map(e => e.type))];
  const count = lines.value === 'off' ? 0 : edges.length;
  const legend = element('legend');
  legend.replaceChildren(node('span', '当前 ' + visible.length + ' 门 · ' + count + ' 条连线'));
  if (count) for (const k of kinds) {
    const [label, color, dash] = typeOf({type:k});
    const sample = node('span', null, 'line-key');
    const stroke = node('i');
    stroke.style.borderColor = color;
    stroke.style.borderTopStyle = dash ? 'dashed' : 'solid';
    sample.append(stroke, label);
    legend.append(sample);
  }
  if (groups.has(0)) legend.append(node('span', '春、秋等季节信息保留在课程详情中，具体学期见原方案。'));
  if (lines.value === 'syllabus' && !count && !element('syllabus-label').hidden && !element('syllabus').value) {
    legend.append(node('span', '请选择参考教学班，查看该班大纲明确列出的先修。'));
  }
  scheduleDraw();
}
function scheduleDraw() {
  cancelAnimationFrame(drawFrame);
  drawFrame = requestAnimationFrame(drawLinks);
}
function drawLinks() {
  svg.replaceChildren();
  if (!detail || element('map').hidden || lines.value === 'off') return;
  const rect = graph.getBoundingClientRect();
  const cards = new Map([...columns.querySelectorAll('[data-id]')].map(c => [c.dataset.id, c.getBoundingClientRect()]));
  const paths = document.createDocumentFragment();
  const defs = document.createElementNS(svg.namespaceURI, 'defs');
  for (const [type, [, color]] of Object.entries(courseTypes)) {
    if (type === 'content') continue;
    const marker = document.createElementNS(svg.namespaceURI, 'marker');
    for (const [key, value] of Object.entries({id:'arrow-'+type, viewBox:'0 0 8 8', refX:'8', refY:'4', markerWidth:'6', markerHeight:'6', orient:'auto'})) marker.setAttribute(key,value);
    const tip = document.createElementNS(svg.namespaceURI, 'polygon');
    tip.setAttribute('points','0,0 8,4 0,8');
    tip.setAttribute('fill',color);
    marker.append(tip);
    defs.append(marker);
  }
  paths.append(defs);
  for (const edge of currentEdges()) {
    if (lines.value === 'syllabus' && edge.type !== 'syllabus_prerequisite') continue;
    const a = cards.get(String(edge.from)), b = cards.get(String(edge.to));
    if (!a || !b) continue;
    const same = a.left === b.left;
    const forward = a.left < b.left;
    const ax = (forward || same ? a.right : a.left) - rect.left;
    const bx = (forward ? b.left : b.right) - rect.left;
    const ay = a.top + a.height / 2 - rect.top, by = b.top + b.height / 2 - rect.top;
    const curve = same ? ax + 20 : (ax + bx) / 2;
    const [label, color, dash] = typeOf(edge);
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M' + ax + ' ' + ay + ' C' + curve + ' ' + ay + ' ' + curve + ' ' + by + ' ' + bx + ' ' + by);
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-dasharray', dash);
    if (edge.type !== 'content' && courseTypes[edge.type]) path.setAttribute('marker-end','url(#arrow-'+edge.type+')');
    const selected = [String(edge.from), String(edge.to)].includes(focusId);
    path.setAttribute('opacity', focusId && !selected ? '.12' : '.75');
    path.setAttribute('stroke-width', selected ? '2.4' : '1.4');
    path.setAttribute('aria-label', label);
    paths.append(path);
  }
  svg.append(paths);
}
function focusCourse(id, locate = false) {
  focusId = String(id);
  const course = courses.get(focusId);
  if (!course) return;
  if (!inScope(course)) scope.value = 'all';
  renderGraph();
  renderPanel();
  if (locate) {
    const selected = columns.querySelector('[aria-pressed=true]');
    selected?.scrollIntoView({block: 'nearest', inline: 'center'});
    selected?.focus({preventScroll: true});
  } else {
    element('course-panel').scrollIntoView({block: 'nearest'});
  }
}
function renderPanel() {
  const panel = element('course-panel');
  panel.replaceChildren();
  if (!focusId) return;
  const course = courses.get(focusId);
  const box = node('section', null, 'panel');
  const heading = node('div', null, 'panel-heading');
  const close = node('button', '收起课程');
  close.onclick = () => { focusId = ''; renderPanel(); renderGraph(); };
  heading.append(node('h3', course.name), close);
  const modules = Array.isArray(course.module) ? course.module.join('、') : course.module;
  box.append(heading, node('p', [courseCaption(course), termText(course), modules].filter(Boolean).join(' · ')));
  const relations = currentEdges().filter(e => String(e.from) === focusId || String(e.to) === focusId);
  box.append(node('h3', '课程关系 · ' + relations.length));
  if (!relations.length) box.append(node('p', '当前方案尚无这门课的逐条关系记录。'));
  const groups = new Map();
  for (const edge of relations) {
    const outgoing = String(edge.from) === focusId;
    const other = courses.get(String(outgoing ? edge.to : edge.from));
    if (!other) continue;
    const row = node('div', null, 'relation');
    const [label] = typeOf(edge);
    const button = node('button', other.name);
    button.onclick = () => focusCourse(other.id, true);
    row.append(node('strong', label + ' '), document.createTextNode(edge.type === 'content' ? '↔ ' : outgoing ? '→ ' : '← '), button, node('p', edge.basis));
    const positions = [...(edge.rows || [])];
    if (edge.reference) {
      row.append(node('strong', '适用教学班 · ' + sectionLabel(edge)));
      if (edge.scope) row.append(node('p', edge.scope));
      if (edge.locator) positions.push(edge.locator);
      if (edge.source && /^https:\/\//i.test(edge.source)) {
        const source = node('a','查看该教学班大纲');
        source.href = edge.source;
        source.rel = 'noopener';
        source.target = '_blank';
        row.append(source);
      }
    }
    for (const evidence of edge.evidence || []) {
      if (evidence.text) row.append(node('p', evidence.text));
      if (evidence.at) positions.push(evidence.at);
    }
    if (positions.length) row.append(node('code', positions.join('、')));
    const title = edge.type === 'content' ? '内容相关的课程' : outgoing ? '可衔接的课程' : '本课之前的课程';
    if (!groups.has(title)) {
      const section = node('section');
      section.append(node('h4',title));
      groups.set(title, section);
    }
    groups.get(title).append(row);
  }
  box.append(...groups.values());
  panel.append(box);
}
function searchCourse() {
  const value = element('search').value.trim().toLowerCase();
  if (!value) return;
  const found = [...courses.values()].find(c => !c.publicReference && [c.id, c.name, c.code].some(s => String(s ?? '').toLowerCase() === value));
  if (found) focusCourse(found.id, true);
}
async function start() {
  element('retry').hidden = true;
  try {
    const index = await json('data/cohorts/index.json');
    plans = index.plans;
    departmentCategories = index.departmentCategories || {};
    if (!plans.length) throw new Error('目录为空');
    let wanted = plans.find(p => String(p.id) === query.get('plan') && (!query.get('year') || String(p.year) === query.get('year'))) || {year: query.get('year')};
    if (wanted.relatedDepartments?.includes(query.get('department'))) wanted = {...wanted, department:query.get('department'), category:departmentCategories[query.get('department')]};
    filterPlans('', wanted);
  } catch (error) {
    fail('培养方案目录载入失败（' + error.message + '）。', start);
  }
}
for (const id of selectors) element(id).onchange = () => filterPlans(id);
scope.onchange = () => { if (focusId && !inScope(courses.get(focusId))) focusId = ''; renderGraph(); renderPanel(); };
lines.onchange = renderGraph;
element('syllabus').onchange = () => { renderGraph(); renderPanel(); };
columns.onclick = event => {
  const button = event.target.closest('button');
  if (button) focusCourse(button.closest('[data-id]').dataset.id);
};
element('search').onchange = searchCourse;
element('search').onkeydown = event => { if (event.key === 'Enter') searchCourse(); };
new ResizeObserver(scheduleDraw).observe(columns);
start();
