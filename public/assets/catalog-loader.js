'use strict';
window.CatalogLoader={async load(fetchJSON){
 const data=await fetchJSON('catalog.json');
 if(!data.catalog_parts)return data;
 if(!Array.isArray(data.catalog_parts)||!data.catalog_parts.length||data.catalog_parts.some(p=>!/^catalog-scope-\d+\.json$/.test(p)))throw Error('课程目录分片索引无效');
 const chunks=await Promise.all(data.catalog_parts.map(fetchJSON));
 if(chunks.some(p=>!Array.isArray(p.scope)))throw Error('课程目录分片未完整载入');
 data.scope=chunks.flatMap(p=>p.scope);delete data.catalog_parts;
 if(data.scope.length!==data.stats.course_code_groups)throw Error('课程目录数量不完整');
 return data;
}};
