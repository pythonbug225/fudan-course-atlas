import config from './private-assets-config.json' with {type:'json'};
export const PRIVATE_ASSET_VERSION=config.version;
const prefixFor=(version:string)=>'private-course-assets/'+version+'/';
const cache=new Map<string,any>();
const json=(value:unknown,status=200)=>Response.json(value,{status,headers:{'Cache-Control':'private, no-store'}});
const admin=(req:Request,env:any)=>!!req.headers.get('oai-authenticated-user-id')&&!!req.headers.get('oai-authenticated-user-email')&&String(env.REVIEW_ADMIN_EMAILS||'').split(',').some((email:string)=>email.trim().toLowerCase()===req.headers.get('oai-authenticated-user-email')?.trim().toLowerCase());
const digest=async(bytes:BufferSource)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
export type AssetPublisher={tokenHash:string;version:string};
export async function authorizeAssetPublisher(req:Request,env:any,now=Date.now()):Promise<AssetPublisher|null>{
 const path=new URL(req.url).pathname;
 if(!['/api/private-assets/import','/api/private-assets/status','/api/private-assets/finalize'].includes(path))return null;
 const expected=String(env.PRIVATE_ASSET_PUBLISH_KEY||''),key=req.headers.get('x-asset-publish-key')||'';
 if(expected.length<64||key.length!==expected.length||!env.DB)return null;
 let diff=0;for(let i=0;i<expected.length;i++)diff|=key.charCodeAt(i)^expected.charCodeAt(i);if(diff)return null;
 const hash=await digest(new TextEncoder().encode(key));
 await env.DB.prepare('INSERT OR IGNORE INTO private_asset_import_grants (token_hash,asset_version,created_at,expires_at) VALUES (?,?,?,?)').bind(hash,PRIVATE_ASSET_VERSION,now,now+3600000).run();
 const grant=await env.DB.prepare('SELECT asset_version,expires_at,revoked_at FROM private_asset_import_grants WHERE token_hash=?').bind(hash).first();
 return grant&&grant.asset_version===PRIVATE_ASSET_VERSION&&!grant.revoked_at&&grant.expires_at>now?{tokenHash:hash,version:PRIVATE_ASSET_VERSION}:null;
}
async function manifest(env:any,version=PRIVATE_ASSET_VERSION,staging=false){
 if(!staging&&cache.has(version))return cache.get(version);
 const object=await env.BUCKET?.get(prefixFor(version)+(staging?'staging.json':'manifest.json'));if(!object)return null;
 const value=await object.json();if(!staging)cache.set(version,value);return value;
}
async function importStatus(env:any){
 const published=await manifest(env),m=published||await manifest(env,PRIVATE_ASSET_VERSION,true);
 if(!m)return {ready:false,published:false,version:PRIVATE_ASSET_VERSION,reason:'目录未导入',missing:[]};
 const missing=[];for(const pack of m.packs){const object=await env.BUCKET.head(prefixFor(PRIVATE_ASSET_VERSION)+pack.name);if(!object||object.size!==pack.size)missing.push(pack.name);}
 return {ready:missing.length===0,published:!!published,version:PRIVATE_ASSET_VERSION,files:Object.keys(m.files).length,packs:m.packs.length,missing};
}
const uploadHTML=`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>站内资料导入</title><style>body{font:16px/1.8 system-ui;max-width:850px;margin:50px auto;padding:20px;background:#f4f7f2;color:#153f33}button,input{font:inherit;margin:12px 0}pre{white-space:pre-wrap}button{padding:10px 20px}progress{width:100%}</style><h1>站内资料私有存储导入</h1><p>仅管理员可以导入。选择 manifest.json 和全部 pack-xxx.bin 分卷，系统逐卷校验后写入站内私有存储。</p><input id="files" type="file" multiple accept=".json,.bin"><br><button id="start">校验并导入</button><button id="check">检查完整性</button><progress id="progress" value="0" max="1"></progress><pre id="status" role="status"></pre><a href="/index.html#account">返回我的账户</a><script>
const $=s=>document.querySelector(s);async function request(url,options){const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...options}),j=await r.json();if(!r.ok)throw Error(j.error||'导入失败');return j;}
$('#start').onclick=async()=>{const button=$('#start');button.disabled=true;try{const files=[...$('#files').files],m=files.find(f=>f.name==='manifest.json');if(!m)throw Error('缺少 manifest.json');const plan=JSON.parse(await m.text());for(const p of plan.packs)if(!files.some(f=>f.name===p.name&&f.size===p.size))throw Error('缺少分卷或大小不符：'+p.name);$('#progress').max=plan.packs.length+1;$('#status').textContent='正在写入目录…';await request('/api/private-assets/import?name=manifest.json',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:m});$('#progress').value=1;for(const [index,pack]of plan.packs.entries()){$('#status').textContent='正在校验并导入 '+(index+1)+' / '+plan.packs.length+'：'+pack.name;await request('/api/private-assets/import?name='+pack.name,{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:files.find(f=>f.name===pack.name)});$('#progress').value=index+2;}const status=await request('/api/private-assets/finalize',{method:'POST'});$('#status').textContent=JSON.stringify(status,null,2);}catch(e){$('#status').textContent=e.message;}finally{button.disabled=false;}};
$('#check').onclick=async()=>{try{$('#status').textContent=JSON.stringify(await request('/api/private-assets/status'),null,2);}catch(e){$('#status').textContent=e.message;}};
</script></html>`;
export async function privateAssetResponse(req:Request,env:any,publisher:AssetPublisher|null=null):Promise<Response|null>{
 const url=new URL(req.url);let path;try{path=decodeURIComponent(url.pathname);}catch{return json({error:'地址无效。'},400);}
 const allowed=admin(req,env)||publisher?.version===PRIVATE_ASSET_VERSION;
 if(path==='/admin-assets')return admin(req,env)?new Response(uploadHTML,{headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'private, no-store'}}):json({error:'仅管理员可以导入。'},403);
 if(path.startsWith('/api/private-assets/')){
  if(!allowed)return json({error:'仅管理员或有效发布任务可以操作。'},403);
  if(!env.BUCKET)return json({error:'私有存储未配置。'},503);
  if(path==='/api/private-assets/status')return req.method==='GET'?json(await importStatus(env)):json({error:'Method not allowed'},405);
  if(req.method!=='POST')return json({error:'Method not allowed'},405);
  if(req.headers.get('origin')!==url.origin)return json({error:'请从本站提交。'},403);
  if(path==='/api/private-assets/finalize'){
   const status=await importStatus(env);if(!status.ready)return json({error:'资料分卷尚未齐全。',...status},409);
   const m=await manifest(env)||await manifest(env,PRIVATE_ASSET_VERSION,true);
   await env.BUCKET.put(prefixFor(PRIVATE_ASSET_VERSION)+'manifest.json',JSON.stringify(m),{httpMetadata:{contentType:'application/json'}});
   cache.set(PRIVATE_ASSET_VERSION,m);
   await env.DB.prepare('UPDATE private_asset_import_grants SET revoked_at=? WHERE asset_version=? AND revoked_at IS NULL').bind(Date.now(),PRIVATE_ASSET_VERSION).run();
   return json({...status,published:true,publisherRevoked:true});
  }
  if(path!=='/api/private-assets/import')return json({error:'Not found'},404);
  if(await manifest(env))return json({error:'该资料版本已经发布，请使用新的版本编号。'},409);
  const name=url.searchParams.get('name')||'';
  if(name==='manifest.json'){
   if(Number(req.headers.get('content-length')||0)>8*1024*1024)return json({error:'目录文件过大。'},413);
   const raw=await req.text();if(raw.length>8*1024*1024)return json({error:'目录文件过大。'},413);
   let m;try{m=JSON.parse(raw);}catch{return json({error:'目录格式无效。'},400);}
   if(m.version!==PRIVATE_ASSET_VERSION||!Array.isArray(m.packs)||m.packs.length>100||!m.files||typeof m.files!=='object')return json({error:'目录版本或格式不正确。'},400);
   for(const pack of m.packs)if(!/^pack-\d{3}\.bin$/.test(pack.name)||!Number.isSafeInteger(pack.size)||pack.size<0||pack.size>32*1024*1024||!/^([a-f0-9]{64})$/.test(pack.sha256))return json({error:'分卷信息无效。'},400);
   for(const [file,value]of Object.entries(m.files) as [string,any][]){const pack=m.packs.find((pack:any)=>pack.name===value.pack);if(!value||!file.startsWith('/')||file.includes('..')||!pack||!Number.isSafeInteger(value.offset)||!Number.isSafeInteger(value.size)||value.offset<0||value.size<0||value.offset+value.size>pack.size)return json({error:'文件索引无效。'},400);}
   if(publisher){const hash=await digest(new TextEncoder().encode(raw));const result=await env.DB.prepare('UPDATE private_asset_import_grants SET manifest_hash=? WHERE token_hash=? AND (manifest_hash IS NULL OR manifest_hash=?) AND revoked_at IS NULL').bind(hash,publisher.tokenHash,hash).run();if(!result.meta?.changes)return json({error:'发布任务已绑定另一份资料目录。'},409);}
   await env.BUCKET.put(prefixFor(PRIVATE_ASSET_VERSION)+'staging.json',raw,{httpMetadata:{contentType:'application/json'}});return json({ok:true,files:Object.keys(m.files).length});
  }
  const m=await manifest(env,PRIVATE_ASSET_VERSION,true),pack=m?.packs.find((pack:any)=>pack.name===name);if(!pack)return json({error:'请先导入匹配版本的目录。'},400);
  if(Number(req.headers.get('content-length')||0)>32*1024*1024)return json({error:'分卷过大。'},413);
  const bytes=await req.arrayBuffer();if(bytes.byteLength!==pack.size)return json({error:'分卷大小不符。'},400);
  if(await digest(bytes)!==pack.sha256)return json({error:'分卷校验失败。'},400);
  await env.BUCKET.put(prefixFor(PRIVATE_ASSET_VERSION)+name,bytes);return json({ok:true,name,size:bytes.byteLength});
 }
 if(path.startsWith('/api/'))return null;
 const filePath=path==='/'||path==='/index'?'/index.html':path;
 let file:any,version=PRIVATE_ASSET_VERSION,anyManifest=false;
 for(const candidate of [PRIVATE_ASSET_VERSION,...config.fallbackVersions]){const m=await manifest(env,candidate);if(m)anyManifest=true;if(m?.files[filePath]){file=m.files[filePath];version=candidate;break;}}
 if(!file){if(['/login.html','/login','/assets/student-login.js','/assets/student-login.css'].includes(path))return null;if(!anyManifest)return new Response('站内资料正在准备，请稍后刷新。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8','Cache-Control':'private, no-store'}});return null;}
 if(!['GET','HEAD'].includes(req.method))return json({error:'Method not allowed'},405);
 let offset=0,length=file.size,status=200;const range=req.headers.get('range');
 if(range){const match=/^bytes=(\d*)-(\d*)$/.exec(range);if(!match||(!match[1]&&!match[2]))return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+file.size}});if(match[1]){offset=Number(match[1]);length=(match[2]?Math.min(Number(match[2]),file.size-1):file.size-1)-offset+1;}else{length=Math.min(Number(match[2]),file.size);offset=file.size-length;}if(offset>=file.size||length<=0)return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+file.size}});status=206;}
 const headers:Record<string,string>={'Content-Type':file.type,'Content-Length':String(length),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Accept-Ranges':'bytes','X-Robots-Tag':'noindex, nofollow, noarchive','X-Private-Asset-Version':version};
 if(status===206)headers['Content-Range']='bytes '+offset+'-'+(offset+length-1)+'/'+file.size;
 if(req.method==='HEAD')return new Response(null,{status,headers});if(length===0)return new Response('',{status,headers});
 const object=await env.BUCKET.get(prefixFor(version)+file.pack,{range:{offset:file.offset+offset,length}});
 if(!object)return new Response('该资料暂时无法读取，请稍后刷新。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8','Cache-Control':'private, no-store'}});
 return new Response(object.body,{status,headers});
}
