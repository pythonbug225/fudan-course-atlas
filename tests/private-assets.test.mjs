import test from 'node:test';
import assert from 'node:assert/strict';
import {D1} from './helpers/d1.mjs';
import {privateAssetResponse,PRIVATE_ASSET_VERSION} from '../lib/private-assets.ts';
test('private pack import verifies hashes and serves exact offsets, unicode files and ranges',async()=>{
 const objects=new Map();const env={DB:new D1(),REVIEW_ADMIN_EMAILS:'owner@example.test',BUCKET:{
  async put(key,body){objects.set(key,typeof body==='string'?new TextEncoder().encode(body):new Uint8Array(body));},
  async get(key,options){const bytes=objects.get(key);if(!bytes)return null;return {body:options?.range?bytes.slice(options.range.offset,options.range.offset+options.range.length):bytes,json:async()=>JSON.parse(new TextDecoder().decode(bytes))};},
  async head(key){return objects.has(key)?{size:objects.get(key).length}:null;}
 }};
 const oldPrefix='private-course-assets/20261105-student-v1/';
 await env.BUCKET.put(oldPrefix+'old.bin','previous');
 await env.BUCKET.put(oldPrefix+'manifest.json',JSON.stringify({files:{'/index.html':{pack:'old.bin',offset:0,size:8,type:'text/html'}}}));
 const bytes=new TextEncoder().encode('page-contents{"course":"test"}'),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
 const manifest={version:PRIVATE_ASSET_VERSION,packs:[{name:'pack-000.bin',size:bytes.length,sha256:hash}],files:{'/index.html':{pack:'pack-000.bin',offset:0,size:13,type:'text/html'},'/中文.json':{pack:'pack-000.bin',offset:13,size:bytes.length-13,type:'application/json'}}};
 const request=(path,{body,admin=false,range}={})=>new Request('https://atlas.test'+path,{method:body?'POST':'GET',headers:{origin:'https://atlas.test',...(admin?{'oai-authenticated-user-id':'owner','oai-authenticated-user-email':'owner@example.test'}:{}),...(range?{range}:{})},body});
 assert.equal((await privateAssetResponse(request('/admin-assets'),env)).status,403);
 assert.equal((await privateAssetResponse(request('/api/private-assets/import?name=manifest.json',{body:JSON.stringify(manifest)}),env)).status,403);
 assert.equal((await privateAssetResponse(request('/api/private-assets/import?name=manifest.json',{admin:true,body:JSON.stringify(manifest)}),env)).status,200);
 assert.equal(await (await privateAssetResponse(request('/index.html'),env)).text(),'previous');
 assert.equal((await privateAssetResponse(request('/api/private-assets/import?name=pack-000.bin',{admin:true,body:new Uint8Array(bytes.length)}),env)).status,400);
 assert.equal((await privateAssetResponse(request('/api/private-assets/status',{admin:true}),env)).status,200);
 await privateAssetResponse(request('/api/private-assets/import?name=pack-000.bin',{admin:true,body:bytes}),env);
 assert.equal((await (await privateAssetResponse(request('/api/private-assets/status',{admin:true}),env)).json()).ready,true);
 assert.equal(await (await privateAssetResponse(request('/index.html'),env)).text(),'previous');
 assert.equal((await privateAssetResponse(request('/api/private-assets/finalize',{admin:true,body:'{}'}),env)).status,200);
 const page=await privateAssetResponse(request('/index.html'),env);assert.equal(await page.text(),'page-contents');assert.match(page.headers.get('cache-control'),/no-store/);
 const data=await privateAssetResponse(request('/%E4%B8%AD%E6%96%87.json'),env);assert.equal(await data.text(),'{"course":"test"}');
 const range=await privateAssetResponse(request('/index.html',{range:'bytes=5-8'}),env);assert.equal(range.status,206);assert.equal(await range.text(),'cont');assert.equal(range.headers.get('content-range'),'bytes 5-8/13');
 assert.equal((await privateAssetResponse(request('/index.html',{range:'bytes=1000-2000'}),env)).status,416);
 assert.equal((await privateAssetResponse(request('/api/private-assets/import?name=manifest.json',{admin:true,body:JSON.stringify(manifest)}),env)).status,409);
});
test('import endpoints reject a retired import key without administrator login',async()=>{
 const req=new Request('https://atlas.test/api/private-assets/status',{headers:{'x-private-import-key':'test-fixture-'.repeat(8)}});
 assert.equal((await privateAssetResponse(req,{PRIVATE_ASSET_IMPORT_KEY:'test-fixture-'.repeat(8)})).status,403);
});
