import fs from 'node:fs/promises';import path from 'node:path';
const root=process.cwd(),ignored=new Set(['node_modules','.git','.sites-runtime','.wrangler','.vinext','.next']);
let count=0,bytes=0;const findings=[];
async function walk(dir){for(const e of await fs.readdir(dir,{withFileTypes:true})){if(ignored.has(e.name))continue;const f=path.join(dir,e.name);if(e.isDirectory())await walk(f);else{const b=await fs.readFile(f);count++;bytes+=b.length;if(/\.(js|mjs|cjs|ts|tsx|json|html|css|md|txt|py|env)$/i.test(e.name)){if(/\bsk-[A-Za-z0-9_-]{24,160}\b/.test(b.toString('utf8')))findings.push(path.relative(root,f));}if(/^\.env|^\.dev.vars/.test(e.name))findings.push(path.relative(root,f));}}}
await walk(root);console.log(JSON.stringify({files:count,bytes,credentialFindings:findings}));if(findings.length)process.exit(1);
