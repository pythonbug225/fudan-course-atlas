// Keep editable JSON in source; deploy a lossless gzip copy to stay within hosting limits.
import fs from 'node:fs/promises';
import path from 'node:path';
import { gzipSync, gunzipSync } from 'node:zlib';
import assert from 'node:assert/strict';
const root=path.resolve('dist/client'),names=['course-summaries.json','enrollment.json',...(await fs.readdir(path.join(root,'data'))).filter(n=>/^syllabus-fallback(?:-\d+)?\.json$/.test(n))];
let before=0,after=0;
for(const name of names){
 const file=path.join(root,'data',name),original=await fs.readFile(file),packed=gzipSync(original,{level:9});
 assert(gunzipSync(packed).equals(original));await fs.writeFile(file+'.gz',packed);await fs.unlink(file);before+=original.length;after+=packed.length;
}
await fs.writeFile(path.join(root,'assets/course-data-delivery.js'),'window.COURSE_DATA_COMPRESSED=true;window.COURSE_DATA_PACKED_FILES='+JSON.stringify(names.map(n=>'data/'+n))+';\n');
console.log(`Lossless JSON delivery: ${names.length} files, ${before} -> ${after} bytes; editable source JSON retained.`);
