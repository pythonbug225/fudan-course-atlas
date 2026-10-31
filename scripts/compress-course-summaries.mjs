// Keep editable JSON in source; deploy a lossless gzip copy to stay within hosting limits.
import fs from 'node:fs/promises';
import path from 'node:path';
import { gzipSync, gunzipSync } from 'node:zlib';
import assert from 'node:assert/strict';
const root=path.resolve('dist/client'),file=path.join(root,'data/course-summaries.json');
const original=await fs.readFile(file),packed=gzipSync(original,{level:9});
assert(gunzipSync(packed).equals(original));
await fs.writeFile(file+'.gz',packed);
await fs.unlink(file);
await fs.writeFile(path.join(root,'assets/course-data-delivery.js'),'window.COURSE_DATA_COMPRESSED=true;\n');
console.log(`Lossless summary delivery: ${original.length} -> ${packed.length} bytes; source JSON retained.`);
