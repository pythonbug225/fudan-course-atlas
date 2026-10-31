// Earlier import tests retain their original cohorts while the all-school test
// checks every newly fetched official section and recursive plan entry.
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib');
const base=path.resolve(__dirname,'../research/contributions/all-school-audit-20261031');
const categories=JSON.parse(fs.readFileSync(path.join(base,'baseline-course-categories.json'),'utf8'));
const official=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(base,'official-sections.json.gz'))));
const bySection=new Map(official.concat(JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(base,'2026-autumn-sections.json.gz'))))).map(x=>[x[0]+'|'+x[2].toUpperCase(),x]));
const report=JSON.parse(fs.readFileSync(path.join(base,'integration-report.full.json'),'utf8'));
const normalizedNames=ts=>[...new Set(ts.map(t=>t.replace(/[A-Za-z ]+[（(]([\u4e00-\u9fff]{2,5})[）)]/g,'$1').trim()))].sort();
module.exports={normalizedNames,latestSyllabus:(id,term,section)=>{const b=report.syllabus_downloads.bindings.find(b=>b.course_id===id&&b.term===term&&b.section_code===section);return b?[term,b.lesson_id,section,'','','','',b.teachers]:null;},baseline:g=>Object.hasOwn(categories,g.id),official:(term,code)=>bySection.get(term+'|'+code.toUpperCase()),
 refreshed:(id,term,section)=>report.syllabus_downloads.bindings.some(b=>b.course_id===id&&b.term===term&&b.section_code===section)};
