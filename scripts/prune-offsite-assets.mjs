// Large reference downloads are preserved in GitHub and omitted from the deploy archive.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
const root=path.resolve('dist/client');
const manifest=JSON.parse(await fs.readFile(path.join(root,'data/offsite-assets.json'),'utf8'));
let removed=0;
for(const item of manifest.assets){
 assert(item.path.startsWith('assets/')&&item.path.split('/').every(p=>/^[a-zA-Z0-9._-]+$/.test(p)&&p!=='.'&&p!=='..'));
 assert(item.url.startsWith('https://github.com/pythonbug225/fudan-course-atlas/releases/download/')||/^https:\/\/raw\.githubusercontent\.com\/pythonbug225\/fudan-course-atlas\/[a-f0-9]{40}\/public\/assets\//.test(item.url));
 const file=path.resolve(root,item.path);
 assert(file.startsWith(root+path.sep));
 const data=await fs.readFile(file);
 assert.equal(crypto.createHash('sha256').update(data).digest('hex'),item.sha256,item.path);
 await fs.unlink(file);removed+=data.length;
}
console.log(`Reference downloads retained in GitHub; omitted ${removed} bytes from deploy archive.`);
