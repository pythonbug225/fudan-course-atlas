'use strict';
const DATA = JSON.parse(document.getElementById('graph-data').textContent);
const NODES = new Map(DATA.nodes.map(n => [n.id, n]));
const TOPICS = new Map(DATA.topics.map(t => [t.id, t.label]));
const labels = Object.fromEntries(Object.entries(DATA.relation_types).map(([k,v]) => [k,v.label]));
const $ = id => document.getElementById(id);
let current = NODES.has(location.hash.slice(1)) ? location.hash.slice(1) : 'PHIL20013';
const svgNS = 'http://www.w3.org/2000/svg';
function element(tag, text, parent) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (parent) parent.appendChild(el);
  return el;
}
function svgElement(tag, attrs, parent) {
  const el = document.createElementNS(svgNS,tag);
  for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
  if (parent) parent.appendChild(el);
  return el;
}
for (const topic of DATA.topics) { const option=element('option',topic.label,$('topic')); option.value=topic.id; }
for (const [kind,label] of Object.entries(labels)) { const option=element('option',label,$('kind')); option.value=kind; }
function matches(n) {
  const query=$('search').value.trim().toLocaleLowerCase();
  return (!$('topic').value || n.topics.includes($('topic').value)) &&
    (!query || [n.id,n.name,...n.teachers].join(' ').toLocaleLowerCase().includes(query));
}
function visibleEdges() { return DATA.edges.filter(e => (e.source===current || e.target===current) && (!$('kind').value || e.kind===$('kind').value)); }
function other(e) { return e.source===current ? e.target : e.source; }
function select(id) {
  current=id;
  history.replaceState(null,'','#'+id);
  renderList();renderDetail();
}
function renderList() {
  const root=$('courses');root.replaceChildren();
  const filtered=DATA.nodes.filter(matches);
  $('count').textContent=`${filtered.length} / ${DATA.nodes.length} 个课程代码`;
  for (const n of filtered) {
    const button=element('button',n.name,root);button.type='button';
    element('small',n.id+' · '+n.levels.join(' / '),button);
    button.classList.toggle('active',n.id===current);button.setAttribute('aria-pressed',String(n.id===current));
    button.addEventListener('click',()=>select(n.id));
  }
  if (!filtered.length) element('p','没有匹配的课程。',root);
}
function renderDetail() {
  const n=NODES.get(current);const edges=visibleEdges();
  $('selected').textContent=n.name;$('code').textContent=n.id+' · '+n.teachers.join('、');
  $('meta').replaceChildren();
  for (const label of [...n.levels,...n.terms,...n.topics.map(t=>TOPICS.get(t))]) element('span',label,$('meta'));
  $('scope').textContent='正式先修要求：尚待核实。当前课程是否出现在左侧筛选结果中，不影响它的完整相邻关系。';
  const body=$('relationships');body.replaceChildren();
  const sorted=[...edges].sort((a,b)=>a.kind.localeCompare(b.kind)||other(a).localeCompare(other(b)));
  $('relationship-count').textContent=`${edges.length} 条关系；表格完整列出当前关系类型筛选下的结果。`;
  for (const e of sorted) {
    const neighbor=NODES.get(other(e));const row=element('tr',undefined,body);
    const first=element('td',undefined,row);const button=element('button',neighbor.name,first);button.type='button';button.addEventListener('click',()=>select(neighbor.id));element('small',neighbor.id,first);
    const second=element('td',labels[e.kind],row);
    element('small',e.directed?(e.source===current?'本课 → 关联课':'关联课 → 本课'):'无方向',second);
    const third=element('td',e.rationale,row);third.className='reason';
    element('small',(e.authority==='official'?'官方规则':'编辑推断')+' · '+e.id+' · '+e.evidence.map(x=>x.source_id+' / '+x.locator).join('；'),third);
    if(e.scope) element('small','适用范围：'+e.scope,third);
  }
  if(!edges.length) { const row=element('tr',undefined,body);const cell=element('td','当前类型没有已记录关系；这不表示没有先修要求。',row);cell.colSpan=3; }
  renderGraph(edges);
}
function renderGraph(edges) {
  const svg=$('graph');svg.replaceChildren();
  const priority={official_sequence:0,official_credit_waiver:1,recommended_preparation:2,parallel_variant:3,same_title:4,content_related:5};
  const best=new Map();
  for(const e of [...edges].sort((a,b)=>priority[a.kind]-priority[b.kind])) if(!best.has(other(e))) best.set(other(e),e);
  const chosen=[...best.entries()].slice(0,18);
  const left=chosen.filter(([,e])=>e.directed&&e.target===current);
  const right=chosen.filter(([,e])=>!(e.directed&&e.target===current));
  const height=Math.max(430,Math.max(left.length,right.length)*88+90);
  svg.setAttribute('viewBox',`0 0 980 ${height}`);svg.style.height=height+'px';
  $('graph-note').textContent=`图中展示 ${chosen.length} 个相邻课程（每对课程优先展示一种关系）；完整依据见下表。窄屏可横向滚动。`;
  const defs=svgElement('defs',{},svg);const marker=svgElement('marker',{id:'arrow',viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'},defs);svgElement('path',{d:'M0,0 L10,5 L0,10 z'},marker);
  const center={x:490,y:height/2};const positions=new Map([[current,center]]);
  for(const [items,x] of [[left,135],[right,845]]) items.forEach(([id],i)=>positions.set(id,{x,y:(i+1)*height/(items.length+1)}));
  for(const [id,e] of chosen) {
    const p=positions.get(id);const from=e.directed&&e.target===current?p:center;const to=from===center?p:center;
    const dx=to.x>from.x?1:-1;const x1=from.x+dx*112;const x2=to.x-dx*112;
    const path=svgElement('path',{d:`M${x1},${from.y} C${(x1+x2)/2},${from.y} ${(x1+x2)/2},${to.y} ${x2},${to.y}`,class:'edge '+e.kind},svg);
    if(e.directed) path.setAttribute('marker-end','url(#arrow)');
    svgElement('title',{},path).textContent=labels[e.kind]+': '+e.rationale;
  }
  for(const [id,p] of positions) {
    const n=NODES.get(id);const group=svgElement('g',{transform:`translate(${p.x-112},${p.y-34})`,class:id===current?'focus':'neighbor',role:'button',tabindex:0,'aria-label':n.name+' '+id},svg);
    svgElement('rect',{width:224,height:68,rx:7},group);
    svgElement('text',{x:12,y:20,class:'code'},group).textContent=id;
    const chars=[...n.name];
    svgElement('text',{x:12,y:40,'font-size':13},group).textContent=chars.slice(0,15).join('');
    if(chars.length>15) svgElement('text',{x:12,y:57,'font-size':13},group).textContent=chars.slice(15,29).join('')+(chars.length>29?'…':'');
    svgElement('title',{},group).textContent=n.name;
    group.style.cursor='pointer';group.addEventListener('click',()=>select(id));group.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(id);}});
  }
  requestAnimationFrame(()=>{const box=svg.parentElement;box.scrollTop=Math.max(0,(height-box.clientHeight)/2);box.scrollLeft=Math.max(0,(svg.clientWidth-box.clientWidth)/2);});
}
$('search').addEventListener('input',renderList);$('topic').addEventListener('change',renderList);$('kind').addEventListener('change',renderDetail);
addEventListener('hashchange',()=>{const id=location.hash.slice(1);if(NODES.has(id)){current=id;renderList();renderDetail();}});
renderList();renderDetail();
