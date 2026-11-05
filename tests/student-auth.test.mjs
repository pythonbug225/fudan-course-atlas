import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import {createStudentAuth} from '../lib/student-auth.ts';
import {checkInResponse,getPointsResponse} from '../lib/points.ts';

class D1 {
  sql = new DatabaseSync(':memory:');
  constructor() { for (const f of readdirSync(new URL('../drizzle/',import.meta.url)).filter(f=>f.endsWith('.sql')).sort()) this.sql.exec(readFileSync(new URL('../drizzle/'+f,import.meta.url),'utf8')); }
  prepare(sql) { const s=this.sql.prepare(sql); return {bind:(...v)=>({first:async()=>s.get(...v)||null,all:async()=>({results:s.all(...v)}),run:async()=>s.run(...v)})}; }
  async batch(items) { this.sql.exec('BEGIN'); try { const v=[]; for (const s of items)v.push(await s.run());this.sql.exec('COMMIT');return v; }catch(e){this.sql.exec('ROLLBACK');throw e;} }
}
const password = 'test-only-long-password';
function fixture() {
  const DB=new D1();let time=Date.now();
  const env={DB,STUDENT_PASSWORD_PEPPER:'test-fixture-pepper-only',REVIEW_ADMIN_EMAILS:'owner@example.test'};
  return {DB,auth:createStudentAuth(env,()=>time),advance:ms=>time+=ms};
}
function req(path,{body,cookie,admin=false,origin='https://atlas.test',headers={},method}={}) {
  return new Request('https://atlas.test'+path,{method:method||(body?'POST':'GET'),headers:{...(body?{'content-type':'application/json',origin}:{}),...(cookie?{cookie}:{}),...(admin?{'oai-authenticated-user-id':'owner','oai-authenticated-user-email':'owner@example.test'}:{}),...headers},body:body?JSON.stringify(body):undefined});
}
async function call(auth,path,options,status=200) {const {response}=await auth.handle(req(path,options));assert.equal(response.status,status);return {data:await response.json(),cookie:response.headers.get('set-cookie')?.split(';')[0],response};}
async function register(f,number='99999990001') {return call(f.auth,'/api/auth/register',{body:{studentNumber:number,password,nickname:'测试同学'}},201);}
async function approve(f,number='99999990001') {const row=f.DB.sql.prepare('SELECT id FROM student_accounts WHERE student_number=?').get(number);await call(f.auth,'/api/auth/decision',{admin:true,body:{id:row.id,status:'approved'}});return row.id;}

test('all course pages, static data, PDFs and API routes require approved login',async()=>{
  const f=fixture();
  for(const path of ['/','/index.html','/data/catalog.json','/references/test.pdf','/assets/app.js','/data/catalog/part-0.json']) {const result=await f.auth.handle(req(path));assert.equal(result.response.status,302,path);assert.match(result.response.headers.get('location'),/^\/login.html/);}
  assert.equal((await f.auth.handle(req('/api/reviews?course=C0055'))).response.status,401);
  for(const path of ['/login.html','/assets/student-login.js','/assets/student-login.css'])assert.ok((await f.auth.handle(req(path))).request,path);
  const status=await call(f.auth,'/api/session');assert.equal(status.data.signedIn,false);assert.equal(status.data.user,null);assert.match(status.response.headers.get('cache-control'),/no-store/);
});
test('registration, approval, correct login, identity isolation, logout and session expiry',async()=>{
  const f=fixture(),r=await register(f);
  assert.equal(r.data.user.status,'pending');assert.equal(r.data.recoveryCode.length,48);assert.match(r.response.headers.get('set-cookie'),/HttpOnly.*SameSite=Lax.*Secure/);
  assert.equal((await f.auth.handle(req('/index.html',{cookie:r.cookie}))).response.status,302);
  await call(f.auth,'/api/auth/register',{body:{studentNumber:'99999990001',password}},409);
  await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990001',password:'wrong'}},401);
  const id=await approve(f);
  const login=await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990001',password,returnTo:'https://evil.test/'}});
  assert.equal(login.data.returnTo,'/index.html');
  const access=await f.auth.handle(req('/api/points',{cookie:login.cookie,headers:{'oai-authenticated-user-id':'forged','oai-authenticated-user-email':'forged@example.test'}}));
  assert.equal(access.request.headers.get('oai-authenticated-user-id'),'student:'+id);assert.equal(access.request.headers.has('oai-authenticated-user-email'),false);
  const status=await call(f.auth,'/api/session',{cookie:login.cookie});assert.equal(status.data.signedIn,true);assert.equal(status.data.isModerator,false);
  const stored=f.DB.sql.prepare('SELECT * FROM student_accounts').get();assert.notEqual(stored.password_hash,password);assert.notEqual(stored.recovery_hash,r.data.recoveryCode);assert.equal(stored.password_hash.length,64);
  assert.equal(JSON.stringify(status.data).includes(stored.password_hash),false);
  await call(f.auth,'/api/auth/logout',{cookie:login.cookie,body:{}});
  assert.equal((await call(f.auth,'/api/session',{cookie:login.cookie})).data.signedIn,false);
  f.advance(8*24*60*60*1000);assert.equal((await call(f.auth,'/api/session',{cookie:r.cookie})).data.signedIn,false);
});
test('reset and password change revoke other sessions; recovery codes rotate',async()=>{
  const f=fixture(),r=await register(f);await approve(f);
  const a=await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990001',password}});
  const b=await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990001',password}});
  const changed=await call(f.auth,'/api/auth/password',{cookie:a.cookie,body:{oldPassword:password,password:'another-test-password'}});
  assert.equal((await call(f.auth,'/api/session',{cookie:b.cookie})).data.signedIn,false);
  assert.equal((await call(f.auth,'/api/session',{cookie:changed.cookie})).data.signedIn,true);
  const reset=await call(f.auth,'/api/auth/recover',{body:{studentNumber:'99999990001',recoveryCode:r.data.recoveryCode,password}});
  assert.notEqual(reset.data.recoveryCode,r.data.recoveryCode);
  assert.equal((await call(f.auth,'/api/session',{cookie:changed.cookie})).data.signedIn,false);
  await call(f.auth,'/api/auth/recover',{body:{studentNumber:'99999990001',recoveryCode:r.data.recoveryCode,password}},400);
});
test('CSRF, unauthorised approval, header impersonation and suspended sessions are blocked',async()=>{
  const f=fixture(),r=await register(f),id=await approve(f);
  await call(f.auth,'/api/auth/logout',{cookie:r.cookie,body:{},origin:'https://evil.test'},403);
  await call(f.auth,'/api/auth/decision',{cookie:r.cookie,body:{id,status:'approved'}},403);
  await call(f.auth,'/api/auth/accounts',{cookie:r.cookie},403);
  assert.equal((await f.auth.handle(req('/index.html',{headers:{'oai-authenticated-user-id':'fake','oai-authenticated-user-email':'stranger@example.test'}}))).response.status,302);
  const list=await call(f.auth,'/api/auth/accounts?status=approved',{admin:true});assert.equal(list.data.accounts.length,1);assert.equal('password_hash' in list.data.accounts[0],false);
  await call(f.auth,'/api/auth/decision',{admin:true,body:{id,status:'suspended',note:'测试停用'}});
  assert.equal((await call(f.auth,'/api/session',{cookie:r.cookie})).data.signedIn,false);
  assert.equal((await f.auth.handle(req('/index.html',{cookie:r.cookie}))).response.status,302);
  await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990001',password}},403);
});
test('login rate limiting and invalid registrations',async()=>{
  const f=fixture();
  await call(f.auth,'/api/auth/register',{body:{studentNumber:'abc',password}},400);
  await call(f.auth,'/api/auth/register',{body:{studentNumber:'99999990001',password:'short'}},400);
  for(let i=0;i<10;i++)await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990002',password:'invalid'}},401);
  await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990002',password:'invalid'}},429);
  f.advance(16*60*1000);await call(f.auth,'/api/auth/login',{body:{studentNumber:'99999990002',password:'invalid'}},401);
});

test('verified POST preserves body and binds points to the student account',async()=>{
  const f=fixture(),registered=await register(f);const id=await approve(f);
  const access=await f.auth.handle(req('/api/points/checkin',{cookie:registered.cookie,body:{test:'body survives'}}));
  assert.deepEqual(await access.request.clone().json(),{test:'body survives'});
  const response=await checkInResponse(access.request,f.DB);assert.equal(response.status,200);
  const summary=await getPointsResponse(access.request,f.DB);assert.equal((await summary.json()).balance,5);
  assert.equal(f.DB.sql.prepare('SELECT user_id FROM point_events').get().user_id,'student:'+id);
});
