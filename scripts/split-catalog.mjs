import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const dir=path.resolve('dist/client/data');
const source=JSON.parse(await fs.readFile(path.join(dir,'catalog.json'),'utf8'));
const targetBytes=4*1024*1024;const parts=[];let chunk=[],bytes=12;
async function flush(){if(!chunk.length)return;const name=`catalog-scope-${String(parts.length+1).padStart(3,'0')}.json`;await fs.writeFile(path.join(dir,name),JSON.stringify({scope:chunk})+'\n');parts.push(name);chunk=[];bytes=12;}
for(const row of source.scope){const size=Buffer.byteLength(JSON.stringify(row))+1;if(bytes+size>targetBytes)await flush();chunk.push(row);bytes+=size;}
await flush();const manifest={...source};delete manifest.scope;manifest.catalog_parts=parts;
await fs.writeFile(path.join(dir,'catalog.json'),JSON.stringify(manifest)+'\n');
const restored={...manifest,scope:(await Promise.all(parts.map(async p=>JSON.parse(await fs.readFile(path.join(dir,p),'utf8'))))).flatMap(x=>x.scope)};delete restored.catalog_parts;
assert.deepEqual(restored,source,'Catalog partition must preserve every course and field');
for(const name of await fs.readdir(dir)){const stat=await fs.stat(path.join(dir,name));assert(stat.size<=26214400,`${name} exceeds hosting file size limit`);}
console.log(`Catalog prepared as ${parts.length} course chunks, ${source.scope.length} courses; lossless reconstruction verified.`);
