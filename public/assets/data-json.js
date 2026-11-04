(function(){
 'use strict';
 async function load(path){
  const packed=window.COURSE_DATA_COMPRESSED===true&&(window.COURSE_DATA_PACKED_FILES||[]).includes(path);
  const response=await fetch(path+(packed?'.gz':''));if(!response.ok)throw Error('课程数据未载入：'+path);
  if(!packed)return response.json();
  const bytes=new Uint8Array(await response.arrayBuffer());
  if(bytes[0]!==31||bytes[1]!==139)return JSON.parse(new TextDecoder().decode(bytes));
  if(typeof DecompressionStream==='function')return JSON.parse(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text());
  const fallback=await fetch('https://raw.githubusercontent.com/pythonbug225/fudan-course-atlas/main/public/'+path);if(!fallback.ok)throw Error('课程数据未载入：'+path);return fallback.json();
 }
 window.CourseDataJSON={load};
})();
