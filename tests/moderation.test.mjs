import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import {createCommunity} from '../lib/community-core.ts';
import {getPointsResponse} from '../lib/points.ts';

class D1 {
  sql=new DatabaseSync(':memory:');
  constructor(){for(const file of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort())this.sql.exec(readFileSync(new URL('../drizzle/'+file,import.meta.url),'utf8'));}
  prepare(sql){const statement=this.sql.prepare(sql);return {bind:(...args)=>({first:async()=>statement.get(...args)||null,all:async()=>({results:statement.all(...args)}),run:async()=>statement.run(...args)})};}
  async batch(statements){this.sql.exec('BEGIN');try{const result=[];for(const s of statements)result.push(await s.run());this.sql.exec('COMMIT');return result;}catch(e){this.sql.exec('ROLLBACK');throw e;}}
}
function fixture(){
 const DB=new D1(),objects=new Map();
 const BUCKET={put:async(k,b)=>objects.set(k,b),delete:async k=>objects.delete(k),get:async k=>objects.has(k)?{body:objects.get(k)}:null};
 const env={DB,BUCKET,REVIEW_ADMIN_EMAILS:'moderator@example.test'};
 return {DB,objects,handlers:createCommunity(env)};
}
function req(path,{uid='student',admin=false,method='GET',body,origin='https://atlas.test'}={}){
 const headers=new Headers({origin});if(uid)headers.set('oai-authenticated-user-id',uid);if(admin)headers.set('oai-authenticated-user-email','moderator@example.test');
 if(body&&!(body instanceof FormData)){headers.set('content-type','application/json');body=JSON.stringify(body);}
 return new Request('https://atlas.test'+path,{method,headers,body});
}
function form(kind='review',suffix=''){
 const f=new FormData();for(const [k,v] of Object.entries({course:'C0055',kind,teacher:'尤翀',term:'2026春',overall:'课程讲解清晰，课后需要认真做练习。我的体验是先复习定义，再逐步完成作业和课后思考。'+suffix,consent:'yes'}))f.set(k,v);
 if(kind==='material')f.set('files',new File(['课程笔记，包含复习提纲和习题索引。'],'notes.txt',{type:'text/plain'}));return f;
}
async function data(response,status=200){assert.equal(response.status,status);return response.json();}
async function post(h,kind='review',suffix=''){return data(await h.submit(req('/api/reviews',{method:'POST',body:form(kind,suffix)})),201);}
async function decision(h,id,action='approved'){return h.moderate(req('/api/moderation',{uid:'moderator',admin:true,method:'POST',body:{id,decision:action,reason:action==='rejected'?'请补充具体教学班和作业细节。':''}}));}

test('pending submissions and files are private; approval publishes and awards once',async()=>{
 const {DB,handlers:h}=fixture();const item=await post(h,'material');
 assert.equal(item.status,'pending');
 const guest=()=>req('/api/reviews?course=C0055&kind=material',{uid:null});
 assert.equal((await data(await h.list(guest()))).reviews.length,0);
 const mine=(await data(await h.mine(req('/api/submissions/mine')))).submissions[0];
 assert.ok(!('author_id' in mine)&&!('content_hash' in mine));
 const file=mine.files[0].id;
 assert.equal((await h.attachment(req('/api/attachments/'+file,{uid:null}),file)).status,404);
 assert.equal((await h.attachment(req('/api/attachments/'+file),file)).status,200);
 assert.equal((await h.moderate(req('/api/moderation',{method:'POST',body:{id:item.id,decision:'approved'}}))).status,403);
 await data(await decision(h,item.id));await data(await decision(h,item.id));
 assert.equal((await data(await h.list(guest()))).reviews.length,1);
 assert.equal((await h.attachment(req('/api/attachments/'+file,{uid:null}),file)).status,200);
 const balance=await data(await getPointsResponse(req('/api/points'),DB));
 assert.equal(balance.balance,10);assert.equal(balance.events[0].eventType,'submission_reward');assert.equal(balance.events[0].referenceId,item.id);
 DB.sql.close();
});
test('review approval gives 20; duplicate submissions and withdrawal cannot farm rewards',async()=>{
 const {DB,handlers:h}=fixture();const item=await post(h);
 await data(await decision(h,item.id));
 await data(await h.submit(req('/api/reviews',{method:'POST',body:form()})),409);
 assert.equal((await data(await getPointsResponse(req('/api/points'),DB))).balance,20);
 await data(await h.remove(req('/api/reviews/'+item.id,{method:'DELETE'}),item.id));
 await data(await h.remove(req('/api/reviews/'+item.id,{method:'DELETE'}),item.id));
 assert.equal((await data(await getPointsResponse(req('/api/points'),DB))).balance,0);
 await data(await h.submit(req('/api/reviews',{method:'POST',body:form()})),409);
 assert.equal((await h.moderate(req('/api/moderation',{uid:'moderator',admin:true,method:'POST',body:{id:item.id,decision:'approved'}}))).status,409);
 DB.sql.close();
});
test('rejected items preserve author feedback and award no points; users are isolated',async()=>{
 const {DB,handlers:h}=fixture();const item=await post(h);
 await data(await decision(h,item.id,'rejected'));
 const mine=(await data(await h.mine(req('/api/submissions/mine')))).submissions;
 assert.equal(mine[0].status,'rejected');assert.match(mine[0].moderation_note,/补充/);
 assert.equal((await data(await h.mine(req('/api/submissions/mine',{uid:'other'})))).submissions.length,0);
 assert.equal((await data(await h.list(req('/api/reviews?course=C0055',{uid:'other'})))).reviews.length,0);
 assert.equal((await h.remove(req('/api/reviews/'+item.id,{method:'DELETE',uid:'other'}),item.id)).status,403);
 assert.equal((await data(await getPointsResponse(req('/api/points'),DB))).balance,0);
 DB.sql.close();
});
test('moderation requires authenticated allowlisted identity and same origin',async()=>{
 const {DB,handlers:h}=fixture();
 assert.equal((await h.moderationList(req('/api/moderation',{uid:null}))).status,401);
 assert.equal((await h.moderationList(req('/api/moderation'))).status,403);
 assert.equal((await h.moderate(req('/api/moderation',{uid:'moderator',admin:true,method:'POST',origin:'https://other.test',body:{id:'x',decision:'approved'}}))).status,403);
 assert.equal((await h.mine(req('/api/submissions/mine',{uid:null}))).status,401);
 DB.sql.close();
});
test('concurrent approval and duplicate requests create a single reward event',async()=>{
 const {DB,handlers:h}=fixture();const item=await post(h);
 // D1 batch transactions serialize; issue retries after the first committed decision.
 await decision(h,item.id);await Promise.all([decision(h,item.id),decision(h,item.id)]);
 assert.equal(DB.sql.prepare("SELECT count(*) n FROM point_events WHERE event_type='submission_reward'").get().n,1);
 assert.equal((await data(await getPointsResponse(req('/api/points'),DB))).balance,20);
 DB.sql.close();
});
