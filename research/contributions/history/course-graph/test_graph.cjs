const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const loaded=require('./graph-core.js');
const core=loaded.select?loaded:globalThis.HistoryGraph;
const g=JSON.parse(fs.readFileSync(path.join(__dirname,'graph.json'),'utf8'));
assert.equal(core.search(g,'HIST30007')[0].id,'HIST30007');
assert(core.search(g,'仇鹿鸣').length>0);
const ancestors=core.ancestors(g,'HIST40007');
assert(ancestors.has('HIST30071')&&ancestors.has('HIST10002'));
assert(!ancestors.has('HIST60028'));
for(const type of ['all','recommended_prerequisite','content_relation','official_prerequisite']){
  const view=core.select(g,{focus:'HIST30007',mode:'focus',group:'all',level:'all',type,path:''});
  assert(view.edges.every(e=>type==='all'||e.type===type));
}
const view=core.select(g,{focus:'HIST40007',mode:'ancestors',group:'all',level:'all',type:'all',path:''});
assert(view.edges.every(e=>e.directed));
const ug=core.select(g,{focus:'HIST10002',mode:'all',group:'all',level:'本科',type:'all',path:''});
assert(ug.nodes.every(n=>n.levels.includes('本科')));
assert(g.nodes.some(n=>n.id==='HIST30007')&&g.nodes.some(n=>n.id==='HIST60069'));
console.log(JSON.stringify({verification:'passed',search:true,directional_ancestors:true,relation_filters:true,level_filters:true}));
