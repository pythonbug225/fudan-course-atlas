'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const graph=JSON.parse(fs.readFileSync(path.join(__dirname,'graph.json'),'utf8'));
const context={};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'graph-core.js'),'utf8'),context);
const core=context.LawGraph;
const defaults={focus:'LAW10001',mode:'focus',group:'all',level:'all',type:'all',path:''};
assert(core.search(graph,'law20007').some(n=>n.id==='LAW20007h'));
assert(core.search(graph,'民法II').some(n=>n.id==='LAW20007'));
assert.equal(core.search(graph,'不存在的课程').length,0);
const early=core.ancestors(graph,'LAW50049');
assert(early.has('LAW20007')&&early.has('LAW10001')&&early.has('LAW10004'));
assert(!early.has('GEEC10213'),'content-linked course must not become a prerequisite');
const descendants=core.ancestors(graph,'LAW10004');
assert(!descendants.has('LAW10001'),'do not reverse prerequisite direction');
const cycle={edges:[{source:'a',target:'b',type:'recommended_prerequisite'},{source:'b',target:'a',type:'recommended_prerequisite'}]};
assert.equal(core.ancestors(cycle,'a').size,2,'traversal must terminate even on future bad data');
for(const level of ['all','ug','本科','研究生','本研融通'])for(const type of ['all','recommended_prerequisite','content_relation','official_prerequisite']){
  const view=core.select(graph,{...defaults,mode:'all',level,type});const ids=new Set(view.nodes.map(n=>n.id));
  assert(view.edges.every(e=>ids.has(e.source)&&ids.has(e.target)));
  if(type==='official_prerequisite')assert.equal(view.edges.length,0);
  if(level==='研究生')assert(view.nodes.every(n=>n.levels.includes('研究生')));
}
assert.equal(core.select(graph,{...defaults,mode:'all'}).nodes.length,260);
assert(core.select(graph,{...defaults,focus:'GECC10052'}).nodes.some(n=>n.id==='GECC10052'),'isolated courses remain visible');
const honors=core.select(graph,{...defaults,focus:'LAW20007h',type:'recommended_prerequisite'});
assert.equal(honors.edges.length,0,'H class must not inherit ordinary-class suggestions');
for(const p of graph.paths){
  const view=core.select(graph,{...defaults,path:p.id});
  assert.deepEqual(new Set(view.nodes.map(n=>n.id)),new Set(p.codes));
}
const page=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');let scripts=0;
for(const block of page.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)){
  if(block[1].includes('application/json'))continue;
  new vm.Script(block[2],{filename:`index-script-${++scripts}.js`});
}
assert.equal(scripts,2);
console.log('Passed: search, prerequisite direction, cycle termination, 20 filter combinations, H separation, isolated nodes, 11 paths, and all generated JavaScript syntax.');
