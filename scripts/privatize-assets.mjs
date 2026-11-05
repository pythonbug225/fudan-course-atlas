import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
const {version}=JSON.parse(await fs.readFile(new URL('../lib/private-assets-config.json',import.meta.url),'utf8'));
const root=path.resolve('dist/client'),out=path.resolve('.sites-runtime/private-assets',version);
await fs.mkdir(out,{recursive:true});
const publicFiles=new Set(['login.html','assets/student-login.js','assets/student-login.css']);
const types={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.json':'application/json;charset=utf-8','.gz':'application/gzip','.svg':'image/svg+xml','.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.txt':'text/plain;charset=utf-8','.md':'text/plain;charset=utf-8','.woff2':'font/woff2'};
async function walk(dir){let list=[];for(const entry of await fs.readdir(dir,{withFileTypes:true})){const file=path.join(dir,entry.name);if(entry.isDirectory())list.push(...await walk(file));else if(entry.isFile())list.push(file);else throw Error('Unexpected non-file asset: '+file);}return list;}
const files=(await walk(root)).sort();const manifest={version,files:{},packs:[]};let handle,pack,size=0,hash;
async function finish(){if(!handle)return;await handle.close();manifest.packs.push({name:pack,size,sha256:hash.digest('hex')});handle=null;}
async function begin(){pack='pack-'+String(manifest.packs.length).padStart(3,'0')+'.bin';size=0;hash=crypto.createHash('sha256');handle=await fs.open(path.join(out,pack),'w');}
for(const file of files){const relative=path.relative(root,file).split(path.sep).join('/');if(publicFiles.has(relative))continue;
 const bytes=await fs.readFile(file);if(bytes.length>32*1024*1024)throw Error('Asset exceeds private-pack limit: '+relative);
 if(!handle)await begin();if(size&&size+bytes.length>16*1024*1024){await finish();await begin();}
 manifest.files['/'+relative]={pack,offset:size,size:bytes.length,type:types[path.extname(file).toLowerCase()]||'application/octet-stream'};
 await handle.writeFile(bytes);hash.update(bytes);size+=bytes.length;
 if(!file.startsWith(root+path.sep))throw Error('Asset path escaped build root');await fs.unlink(file);
}
await finish();await fs.writeFile(path.join(out,'manifest.json'),JSON.stringify(manifest));
const remaining=await walk(root);if(remaining.some(f=>!publicFiles.has(path.relative(root,f).split(path.sep).join('/'))))throw Error('A private asset remains publicly deployable');
console.log('Private assets: '+Object.keys(manifest.files).length+' files in '+manifest.packs.length+' packs. Public build contains only login assets. Import directory: '+out);
