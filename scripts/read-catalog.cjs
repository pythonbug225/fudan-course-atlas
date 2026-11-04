'use strict';
const fs=require('node:fs'),path=require('node:path');
// Shared reader for source JSON: the catalogue may be a manifest plus ordered chunks.
module.exports=function readJSON(file){
 const data=JSON.parse(fs.readFileSync(file,'utf8'));
 if(!data.catalog_parts)return data;
 const parts=data.catalog_parts;
 if(!Array.isArray(parts)||!parts.length||parts.some(p=>!/^catalog-scope-\d+\.json$/.test(p)))throw Error('Invalid catalogue chunk index');
 const chunks=parts.map(p=>JSON.parse(fs.readFileSync(path.join(path.dirname(file),p),'utf8')));
 if(chunks.some(p=>!Array.isArray(p.scope)))throw Error('Invalid catalogue chunk body');
 data.scope=chunks.flatMap(p=>p.scope);delete data.catalog_parts;
 if(data.scope.length!==data.stats.course_code_groups)throw Error('Incomplete catalogue');
 return data;
};
