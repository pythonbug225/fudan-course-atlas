import test from 'node:test';
import assert from 'node:assert/strict';
import {forwardDeepSeek} from '../lib/compass-model.ts';
const fixtureKey='fixture-only-model-key-123456789';
const req=(body,key=fixtureKey)=>new Request('https://atlas.test/api/compass/model',{method:'POST',headers:{'x-deepseek-key':key},body:typeof body==='string'?body:JSON.stringify(body)});

test('invalid model credentials and oversized conversations never call the provider',async()=>{
 const old=globalThis.fetch;globalThis.fetch=()=>{throw Error('provider must not be called');};
 try{
  const invalid=req({messages:[]},'');
  assert.equal((await forwardDeepSeek(invalid)).status,400);
  assert.equal(invalid.bodyUsed,true,'an early error must finish the incoming request body');
  assert.equal((await forwardDeepSeek(req({messages:[]}))).status,400);
  assert.equal((await forwardDeepSeek(req('x'.repeat(256*1024+1)))).status,413);
 }finally{globalThis.fetch=old;}
});
test('relay fixes provider and model, caps token budget and preserves tool responses',async()=>{
 const old=globalThis.fetch;
 globalThis.fetch=async(url,options)=>{
  assert.equal(url,'https://api.deepseek.com/chat/completions');
  const body=JSON.parse(options.body);assert.equal(body.model,'deepseek-flash');assert.equal(body.stream,false);assert.equal(body.max_tokens,2400);
  assert.equal(body.messages[0].tool_call_id,'call-1');
  return Response.json({choices:[{message:{role:'assistant',tool_calls:[{id:'call-2',type:'function',function:{name:'audit_curriculum',arguments:'{}'}}]}}]});
 };
 try{const response=await forwardDeepSeek(req({model:'other',stream:true,max_tokens:999999,messages:[{role:'tool',tool_call_id:'call-1',content:'{}'}]}));assert.equal(response.status,200);assert.equal((await response.json()).choices[0].message.tool_calls[0].id,'call-2');}
 finally{globalThis.fetch=old;}
});
test('provider errors are sanitised and never include credentials',async()=>{
 const old=globalThis.fetch;globalThis.fetch=async()=>new Response(fixtureKey,{status:401});
 try{const response=await forwardDeepSeek(req({messages:[{role:'user',content:'test'}]}));assert.equal(response.status,401);assert.equal((await response.text()).includes(fixtureKey),false);}
 finally{globalThis.fetch=old;}
});
