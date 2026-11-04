import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import {handleModel} from '../lib/model-relay.mjs';
const root=path.resolve('public'),port=Number(process.env.PORT||8769);
const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml'};
http.createServer(async(req,res)=>{
 try{
  const url=new URL(req.url,'http://127.0.0.1:'+port);
  if(url.pathname==='/api/model'){
   const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>1800000){res.writeHead(413);res.end();return;}chunks.push(chunk);}
   const response=await handleModel(new Request(url,{method:req.method,headers:req.headers,body:Buffer.concat(chunks)}));
   res.writeHead(response.status,Object.fromEntries(response.headers));res.end(Buffer.from(await response.arrayBuffer()));return;
  }
  const file=path.resolve(root,'.'+decodeURIComponent(url.pathname==='/'?'/compass.html':url.pathname));
  if(!file.startsWith(root+path.sep))throw Error('path');
  const bytes=await fs.readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
 }catch{res.writeHead(404);res.end('Not found');}
}).listen(port,'127.0.0.1',()=>console.log('Course Compass http://127.0.0.1:'+port));
