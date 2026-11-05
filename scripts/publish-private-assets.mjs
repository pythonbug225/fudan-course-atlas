import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';

// Supply {base, directory, key} over hidden stdin; credentials never reach disk.
process.stdin.setEncoding('utf8');
if(process.stdin.isTTY)process.stdin.setRawMode(true);
console.log('Ready for private asset publication JSON on stdin (input is hidden).');
const line=await new Promise(resolve=>{let value='';process.stdin.on('data',chunk=>{value+=chunk;const end=value.search(/[\r\n]/);if(end>=0)resolve(value.slice(0,end));});});
process.stdin.pause();if(process.stdin.isTTY)process.stdin.setRawMode(false);
const cfg=JSON.parse(line),base=new URL(cfg.base).origin,root=path.resolve(cfg.directory);
if(!base.startsWith('https://')||typeof cfg.key!=='string'||cfg.key.length<64)throw Error('Invalid publication settings');
const raw=await fs.readFile(path.join(root,'manifest.json')),manifest=JSON.parse(raw);
async function request(route,body){
 const response=await fetch(base+route,{method:body?'POST':'GET',headers:{'User-Agent':'FudanCourseAtlasAssetPublisher/2.0','Origin':base,'X-Asset-Publish-Key':cfg.key,'Content-Type':'application/octet-stream'},body,redirect:'manual',signal:AbortSignal.timeout(90_000)});
 if(!response.ok){const error=new Error('Publication request failed: HTTP '+response.status);error.status=response.status;throw error;}
 return response.json();
}
await request('/api/private-assets/import?name=manifest.json',raw);
console.log('Manifest staged; existing published files remain active.');
for(const [index,pack]of manifest.packs.entries()){
 if(!/^pack-\d{3}\.bin$/.test(pack.name))throw Error('Invalid pack name');
 const body=await fs.readFile(path.join(root,pack.name));
 if(body.length!==pack.size||crypto.createHash('sha256').update(body).digest('hex')!==pack.sha256)throw Error('Pack checksum mismatch: '+pack.name);
 for(let attempt=0;;attempt++){
  try{await request('/api/private-assets/import?name='+pack.name,body);break;}
  catch(error){if(attempt>=2||![500,502,503,504].includes(error.status))throw error;}
 }
 console.log('Validated and uploaded '+(index+1)+'/'+manifest.packs.length+': '+pack.name);
}
const status=await request('/api/private-assets/status');
if(!status.ready||status.files!==Object.keys(manifest.files).length||status.missing.length)throw Error('Publication is incomplete');
const result=await request('/api/private-assets/finalize',Buffer.from('{}'));
if(!result.published||!result.publisherRevoked)throw Error('Publication did not finalize');
let revoked=false;
try{await request('/api/private-assets/status');}catch(error){revoked=error.status===401;}
if(!revoked)throw Error('Retired publication key must return HTTP 401');
console.log(JSON.stringify({...result,keyRevoked:true,totalBytes:manifest.packs.reduce((n,p)=>n+p.size,0)}));
