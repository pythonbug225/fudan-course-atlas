import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
export class D1 {
 sql=new DatabaseSync(':memory:');beforeRun=null;
 constructor(){for(const name of readdirSync(new URL('../../drizzle/',import.meta.url)).filter(n=>n.endsWith('.sql')).sort())this.sql.exec(readFileSync(new URL('../../drizzle/'+name,import.meta.url),'utf8'));}
 prepare(sql){const s=this.sql.prepare(sql);return {bind:(...args)=>({first:async()=>s.get(...args)||null,all:async()=>({results:s.all(...args)}),run:async()=>{if(this.beforeRun)await this.beforeRun(sql,args);const r=s.run(...args);return {meta:{changes:Number(r.changes)}};}})};}
 async batch(statements){this.sql.exec('BEGIN');try{const result=[];for(const s of statements)result.push(await s.run());this.sql.exec('COMMIT');return result;}catch(e){this.sql.exec('ROLLBACK');throw e;}}
}
export class Bucket {
 objects=new Map();
 async put(key,body){this.objects.set(key,typeof body==='string'?new TextEncoder().encode(body):new Uint8Array(body));}
 async get(key,options){const bytes=this.objects.get(key);if(!bytes)return null;return {body:options?.range?bytes.slice(options.range.offset,options.range.offset+options.range.length):bytes,json:async()=>JSON.parse(new TextDecoder().decode(bytes))};}
 async head(key){return this.objects.has(key)?{size:this.objects.get(key).length}:null;}
}
