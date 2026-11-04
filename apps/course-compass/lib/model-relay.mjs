import {TOOLS,SYSTEM,FINAL_STYLE} from '../public/agent.js';
export async function handleModel(request) {
  if(request.method!=='POST')return Response.json({error:'请使用 POST'},{status:405});
  const origin=request.headers.get('origin');
  if(origin&&origin!==new URL(request.url).origin)return Response.json({error:'来源不匹配'},{status:403});
  const key=request.headers.get('x-deepseek-key')||'';
  if(!/^sk-[A-Za-z0-9_-]{16,160}$/.test(key))return Response.json({error:'请在设置中连接 DeepSeek API Key'},{status:401});
  try{
    if(Number(request.headers.get('content-length')||0)>1800000)return Response.json({error:'对话过长，请开始新一轮规划'},{status:413});
    const text=await request.text();if(text.length>1800000)return Response.json({error:'对话过长，请开始新一轮规划'},{status:413});
    const input=JSON.parse(text);
    if(!Array.isArray(input.messages)||input.messages.length>180)throw Error('对话格式不正确或已达到本轮长度上限');
    const messages=[{role:'system',content:SYSTEM+'\n'+FINAL_STYLE},...input.messages.filter(m=>['user','assistant','tool'].includes(m.role))];
    const r=await fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:'deepseek-flash',messages,tools:TOOLS,thinking:{type:'disabled'},max_tokens:2400}),signal:AbortSignal.timeout(55000)});
    if(!r.ok)return Response.json({error:r.status===401?'DeepSeek 密钥无效':r.status===402?'DeepSeek 余额不足':r.status===429?'DeepSeek 请求频率限制，请稍后重试':'DeepSeek 服务返回 '+r.status},{status:r.status>=500?502:r.status});
    return Response.json(await r.json(),{headers:{'Cache-Control':'no-store'}});
  }catch(e){return Response.json({error:e.name==='TimeoutError'?'模型响应超时，请重试':'模型请求未完成，请检查连接或对话格式'},{status:502});}
}
