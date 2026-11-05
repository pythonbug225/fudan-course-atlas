import test from 'node:test';
import assert from 'node:assert/strict';
import {D1,Bucket} from './helpers/d1.mjs';
import {authorizeAssetPublisher,privateAssetResponse,PRIVATE_ASSET_VERSION} from '../lib/private-assets.ts';
test('publisher is scoped, bound to a manifest, and irrevocably revoked across requests after finalization',async()=>{
 const key='test-publisher-fixture-'.repeat(5),env={DB:new D1(),BUCKET:new Bucket(),PRIVATE_ASSET_PUBLISH_KEY:key};
 const req=(path,body)=>new Request('https://atlas.test'+path,{method:body?'POST':'GET',headers:{'x-asset-publish-key':key,origin:'https://atlas.test'},body});
 assert.equal(await authorizeAssetPublisher(req('/index.html'),env),null);assert.equal(await authorizeAssetPublisher(req('/api/points'),env),null);
 const grant=await authorizeAssetPublisher(req('/api/private-assets/import?name=manifest.json','placeholder'),env);assert.ok(grant);
 const bytes=new TextEncoder().encode('private-data'),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
 const m={version:PRIVATE_ASSET_VERSION,packs:[{name:'pack-000.bin',size:bytes.length,sha256:hash}],files:{'/index.html':{pack:'pack-000.bin',offset:0,size:bytes.length,type:'text/html'}}};
 assert.equal((await privateAssetResponse(req('/api/private-assets/import?name=manifest.json',JSON.stringify(m)),env,grant)).status,200);
 assert.equal((await privateAssetResponse(req('/api/private-assets/import?name=manifest.json',JSON.stringify({...m,extra:'different'})),env,grant)).status,409);
 await privateAssetResponse(req('/api/private-assets/import?name=pack-000.bin',bytes),env,grant);
 const result=await privateAssetResponse(req('/api/private-assets/finalize','{}'),env,grant);assert.equal((await result.json()).publisherRevoked,true);
 assert.equal(await authorizeAssetPublisher(req('/api/private-assets/status'),{...env}),null);
 assert.equal(await authorizeAssetPublisher(req('/api/private-assets/import?name=manifest.json','{}'),env),null);
 assert.ok(env.DB.sql.prepare('SELECT revoked_at FROM private_asset_import_grants').get().revoked_at);
 assert.equal(env.DB.sql.prepare('SELECT count(*) AS n FROM private_asset_import_grants').get().n,1);
});
test('publisher grants expire and a wrong key never creates a grant',async()=>{
 const key='another-publisher-fixture-'.repeat(4),env={DB:new D1(),PRIVATE_ASSET_PUBLISH_KEY:key};
 const request=value=>new Request('https://atlas.test/api/private-assets/status',{headers:{'x-asset-publish-key':value}});
 assert.equal(await authorizeAssetPublisher(request('wrong-key'),env,1000),null);
 assert.equal(env.DB.sql.prepare('SELECT count(*) AS n FROM private_asset_import_grants').get().n,0);
 assert.ok(await authorizeAssetPublisher(request(key),env,1000));assert.equal(await authorizeAssetPublisher(request(key),env,3601001),null);
});
