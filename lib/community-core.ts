import courses from './course-ids.json' with { type: 'json' };

export function createCommunity(env:any){
 function isModerator(req:Request){
  if(!user(req))return false;
  const email=req.headers.get('oai-authenticated-user-email')?.trim().toLowerCase();
  return !!email && String(env.REVIEW_ADMIN_EMAILS||'').split(',').map((x:string)=>x.trim().toLowerCase()).filter(Boolean).includes(email);
 }
 function publicReview(row:any,uid:string|null,files:any[]=[]){
  const {author_id,moderator_id,content_hash,...visible}=row;
  return {...visible,mine:author_id===uid,files};
 }
 async function contentHash(value:unknown){
  const bytes=value instanceof Uint8Array?value:new TextEncoder().encode(JSON.stringify(value).normalize('NFKC').replace(/\s+/g,' '));
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');
 }
 async function hydrate(rows:any[],req:Request){
  return Promise.all(rows.map(async(row:any)=>{
   const files=await env.DB.prepare('SELECT id,name,mime,size FROM review_files WHERE review_id=?').bind(row.id).all();
   return publicReview(row,user(req),files.results);
  }));
 }
 async function mine(req:Request){
  if(!user(req))return json({error:'请先登录。'},401);
  if(!env.DB)return json({error:'投稿服务暂不可用。'},503);
  const rows=await env.DB.prepare('SELECT * FROM community_reviews WHERE author_id=? ORDER BY created_at DESC,id DESC LIMIT 100').bind(user(req)).all();
  return json({submissions:await hydrate(rows.results,req)});
 }
 async function moderationList(req:Request){
  if(!user(req))return json({error:'请先登录。'},401);
  if(!isModerator(req))return json({error:'仅审核员可以访问。'},403);
  if(!env.DB)return json({error:'投稿服务暂不可用。'},503);
  const status=new URL(req.url).searchParams.get('status')||'pending';
  if(!['pending','approved','rejected'].includes(status))return json({error:'审核状态不正确。'},400);
  const rows=await env.DB.prepare('SELECT * FROM community_reviews WHERE status=? ORDER BY created_at,id LIMIT 100').bind(status).all();
  return json({submissions:await hydrate(rows.results,req)});
 }
 async function moderate(req:Request){
  const denied=checkWrite(req);if(denied)return denied;
  if(!isModerator(req))return json({error:'仅审核员可以操作。'},403);
  let input:any;try{input=await req.json()}catch{return json({error:'请提交有效的审核操作。'},400)}
  const id=String(input.id||''),decision=String(input.decision||''),reason=String(input.reason||'').trim().slice(0,1000);
  if(!id||!['approved','rejected'].includes(decision)||decision==='rejected'&&!reason)return json({error:'退回时请填写修改建议。'},400);
  const row=await env.DB.prepare('SELECT status,kind FROM community_reviews WHERE id=?').bind(id).first();
  if(!row)return json({error:'投稿不存在。'},404);
  if(row.status===decision)return json({id,status:decision,alreadyReviewed:true});
  if(row.status!=='pending')return json({error:'这篇投稿已处理，请刷新列表。'},409);
  const at=new Date().toISOString();
  await env.DB.batch([
   env.DB.prepare("UPDATE community_reviews SET status=?,moderator_id=?,moderated_at=?,moderation_note=? WHERE id=? AND status='pending'").bind(decision,user(req),at,reason,id),
   env.DB.prepare("INSERT OR IGNORE INTO point_events (id,user_id,event_type,event_key,delta,created_at) SELECT ?,author_id,'submission_reward',?,CASE WHEN kind='material' THEN 10 ELSE 20 END,? FROM community_reviews WHERE id=? AND status='approved'").bind(crypto.randomUUID(),'submission:'+id,at,id)
  ]);
  const final=await env.DB.prepare('SELECT status FROM community_reviews WHERE id=?').bind(id).first();
  if(final.status!==decision)return json({error:'投稿状态已变化，请刷新列表。'},409);
  return json({id,status:decision,reward:decision==='approved'?(row.kind==='material'?10:20):0});
 }
const json=(body:unknown,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
function user(req:Request){return req.headers.get('oai-authenticated-user-id');}
function checkWrite(req:Request){
 const origin=req.headers.get('origin');
 if(!origin||origin!==new URL(req.url).origin)return json({error:'请从本站提交。'},403);
 if(!user(req))return json({error:'请先登录后再提交；公开展示时不显示登录身份。'},401);
 if(!env.DB||!env.BUCKET)return json({error:'投稿服务暂不可用，请稍后重试。'},503);
 return null;
}
const text=(form:FormData,key:string,max:number)=>String(form.get(key)||'').trim().slice(0,max);
const allowed=['application/pdf','image/png','image/jpeg','text/plain','text/markdown'];
async function list(req:Request){
 if(!env.DB)return json({error:'投稿服务暂不可用。'},503);
 const url=new URL(req.url),courseId=url.searchParams.get('course'),kind=url.searchParams.get('kind')||'review';
 if(!courseId||!courses.includes(courseId))return json({error:'请选择已收录课程。'},400);
 if(!['review','material'].includes(kind))return json({error:'投稿类型不正确。'},400);
 const rows=await env.DB.prepare("SELECT * FROM community_reviews WHERE course_id=? AND kind=? AND (status IN ('approved','legacy') OR (author_id=? AND status IN ('pending','rejected'))) ORDER BY created_at DESC,id DESC LIMIT 100").bind(courseId,kind,user(req)||'').all();
 const results=await Promise.all(rows.results.map(async(r:any)=>{
  const a=await env.DB!.prepare('SELECT id,name,mime,size FROM review_files WHERE review_id=?').bind(r.id).all();
  return publicReview(r,user(req),a.results);
 }));
 return json({reviews:results,limit:100});
}
async function submit(req:Request){
 const denied=checkWrite(req);if(denied)return denied;
 if(Number(req.headers.get('content-length')||0)>26*1024*1024)return json({error:'附件总量过大。'},413);
 const form=await req.formData(),courseId=text(form,'course',40),teacher=text(form,'teacher',80),term=text(form,'term',20);
 if(!courses.includes(courseId)||!teacher||!/^20\d{2}(春|秋|暑)$/.test(term))return json({error:'请填写课程、教师及学期，例如2026春。'},400);
 const learning=text(form,'learning',5000),workload=text(form,'workload',5000),assessment=text(form,'assessment',5000),grading=text(form,'grading',5000),overall=text(form,'overall',5000);
 const kind=text(form,'kind',20)||'review';
 if(!['review','material'].includes(kind))return json({error:'投稿类型不正确。'},400);
 if(overall.length<(kind==='review'?30:10))return json({error:kind==='review'?'综合体验请至少写30字，具体经历更有帮助。':'请用至少10字说明资料内容和适用范围。'},400);
 if(form.get('consent')!=='yes')return json({error:'请确认公开投稿内容和附件。'},400);
 const uid=user(req)!,since=new Date(Date.now()-86400000).toISOString();
 const count:any=await env.DB!.prepare('SELECT count(*) AS n FROM community_reviews WHERE author_id=? AND created_at>?').bind(uid,since).first();
 if(count.n>=10)return json({error:'24小时内最多提交10篇课评，请稍后再来。'},429);
 const uploads=form.getAll('files').filter((f):f is File=>typeof f!=='string'&&f.size>0);
 if(kind==='material'&&!uploads.length)return json({error:'上传课程资料请至少选择一个附件。'},400);
 if(uploads.length>3||uploads.some(f=>f.size>8*1024*1024))return json({error:'最多3个附件，每个不超过8MB。'},400);
 const rawHours=text(form,'hours',5),hours=rawHours===''?null:Number(rawHours);
 if(hours!==null&&(!Number.isFinite(hours)||hours<0||hours>168))return json({error:'每周用时应为0—168小时。'},400);
 const ready=[];
 for(const f of uploads){
  if(!allowed.includes(f.type))return json({error:'附件支持PDF、PNG、JPG、TXT、Markdown。'},400);
  const bytes=new Uint8Array(await f.arrayBuffer());
  const valid=f.type==='application/pdf'?new TextDecoder().decode(bytes.slice(0,5))==='%PDF-':f.type==='image/png'?bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71:f.type==='image/jpeg'?bytes[0]===255&&bytes[1]===216&&bytes[2]===255:!bytes.includes(0);
  if(!valid)return json({error:'附件格式与内容不符，请重新选择。'},400);
  ready.push({id:crypto.randomUUID(),name:f.name.replace(/[\\/\x00-\x1f]/g,'_').slice(0,150),mime:f.type,bytes});
 }
 const fingerprint=await contentHash([courseId,kind,learning,workload,assessment,grading,overall,...await Promise.all(ready.map(f=>contentHash(f.bytes)))]);
 const duplicate=await env.DB!.prepare('SELECT id FROM community_reviews WHERE author_id=? AND content_hash=?').bind(uid,fingerprint).first();
 if(duplicate)return json({error:'这份内容已经投稿，请在我的投稿中查看状态。'},409);
 const id=crypto.randomUUID(),created=new Date().toISOString(),stored:string[]=[];
 try{
  for(const f of ready){const key='reviews/'+id+'/'+f.id;await env.BUCKET!.put(key,f.bytes,{httpMetadata:{contentType:f.mime}});stored.push(key);}
  await env.DB!.batch([
   env.DB!.prepare('INSERT INTO community_reviews (id,course_id,author_id,teacher,term,class_type,nickname,learning,workload,assessment,grading,overall,grade,hours,created_at,kind,status,content_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)').bind(id,courseId,uid,teacher,term,text(form,'classType',40)||'未注明',text(form,'nickname',30)||'匿名同学',learning,workload,assessment,grading,overall,text(form,'grade',30),hours,created,kind,'pending',fingerprint),
   ...ready.map((f,i)=>env.DB!.prepare('INSERT INTO review_files (id,review_id,object_key,name,mime,size) VALUES (?,?,?,?,?,?)').bind(f.id,id,stored[i],f.name,f.mime,f.bytes.length))
  ]);
  return json({id,created_at:created,status:'pending',reward:kind==='review'?20:10},201);
 }catch(e){await Promise.all(stored.map(k=>env.BUCKET!.delete(k)));if(String(e).includes('UNIQUE'))return json({error:'这份内容已经投稿，请查看我的投稿。'},409);throw e;}
}
async function remove(req:Request,id:string){
 const denied=checkWrite(req);if(denied)return denied;
 const row:any=await env.DB!.prepare('SELECT author_id FROM community_reviews WHERE id=?').bind(id).first();
 if(!row||row.author_id!==user(req))return json({error:'只能撤回自己的投稿。'},403);
 const files=await env.DB!.prepare('SELECT object_key FROM review_files WHERE review_id=?').bind(id).all();
 await env.DB!.batch([
  env.DB!.prepare("UPDATE community_reviews SET status='withdrawn' WHERE id=? AND author_id=?").bind(id,user(req)),
  env.DB!.prepare("INSERT OR IGNORE INTO point_events (id,user_id,event_type,event_key,delta,created_at) SELECT ?,user_id,'submission_withdrawal',?,-delta,? FROM point_events WHERE user_id=? AND event_key=? AND delta>0").bind(crypto.randomUUID(),'withdraw:'+id,new Date().toISOString(),user(req),'submission:'+id),
  env.DB!.prepare('DELETE FROM review_files WHERE review_id=?').bind(id)
 ]);
 await Promise.all(files.results.map((f:any)=>env.BUCKET!.delete(f.object_key)));
 return json({deleted:true});
}
async function attachment(req:Request,id:string){
 if(!env.DB||!env.BUCKET)return json({error:'附件服务暂不可用。'},503);
 const f:any=await env.DB.prepare('SELECT f.*,r.status,r.author_id FROM review_files f JOIN community_reviews r ON r.id=f.review_id WHERE f.id=?').bind(id).first();
 if(!f || (!['approved','legacy'].includes(f.status) && f.author_id!==user(req) && !isModerator(req)))return json({error:'附件不存在或尚未公开。'},404);
 const object=await env.BUCKET.get(f.object_key);if(!object)return json({error:'附件暂不可用。'},404);
 return new Response(object.body,{headers:{'Content-Type':f.mime,'Content-Disposition':"inline; filename*=UTF-8''"+encodeURIComponent(f.name),'X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; sandbox",'Cache-Control':'private, no-store'}});
}

return {json,user,checkWrite,list,submit,remove,attachment,isModerator,mine,moderationList,moderate};
}
