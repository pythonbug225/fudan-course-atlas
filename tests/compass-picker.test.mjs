import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
import {assessmentShares,rollcallSignal,presentationSignal,judgeSection,rankTeachers,bestCombos,parseRequest,matchCourse,cleanPrefs,defaultPrefs} from '../public/compass/picker.js';
import {parseSchedule,overlap} from '../public/compass/engine.js';
const read=p=>JSON.parse(fs.readFileSync(new URL('../public/compass/data/'+p,import.meta.url),'utf8'));
const data=read('catalog.json'),details=read('details.json');
const byId=Object.fromEntries(data.courses.map(c=>[c.id,c]));

const sec=(id,teacher,schedule,assessment=[],extra={})=>({id,code:'TEST.'+id,term:'2026春',teachers:[teacher],credits:2,schedule,assessment,exam:'',class_type:'普通班',...extra});
const A=(final,mid,att,hw=0,pre=0,paper=0)=>[{criteria:'期末考试Final',percentage:final},{criteria:'期中考试Midterm',percentage:mid},{criteria:'出勤Attendance',percentage:att},{criteria:'作业/实验/实践',percentage:hw},{criteria:'汇报Presentation',percentage:pre},{criteria:'课题论文',percentage:paper}].filter(r=>r.percentage);
const course={id:'T1',name:'测试课',code:'TEST',teachers:[]};

test('assessment rows are grouped into exam / attendance / homework shares',()=>{
 const s=assessmentShares({assessment:[{criteria:'期末考试Final Examination：闭卷 ',percentage:50},{criteria:'期中考试Midterm Examination',percentage:30},{criteria:'出勤Attendance',percentage:10},{criteria:'作业/实验/实践Assignment',percentage:10}]});
 assert.deepEqual([s.final,s.midterm,s.attendance,s.homework,s.total],[50,30,10,10,100]);
 assert.equal(assessmentShares({assessment:[]}),null);
});

test('roll-call evidence distinguishes 不点名, 每节点名, plain mentions and conflicting reports',()=>{
 assert.equal(rollcallSignal([{teaching:'',workload:'多届不点名、不pre',assessment:''}]).value,'low');
 assert.equal(rollcallSignal([{teaching:'',workload:'每节点名，请假手续严格',assessment:''}]).value,'high');
 assert.equal(rollcallSignal([{teaching:'',workload:'少量签到之外',assessment:'偶有考勤'}]).value,'low');
 assert.equal(rollcallSignal([{teaching:'',workload:'旧班不点名',assessment:''},{teaching:'',workload:'新评每节点名',assessment:''}]).value,'mixed');
 assert.equal(rollcallSignal([{teaching:'',workload:'课堂练题附名有考勤性质',assessment:''}]).value,'some');
 assert.equal(rollcallSignal([{teaching:'讲得清楚',workload:'',assessment:''}]),null);
 assert.equal(presentationSignal([{teaching:'',workload:'无pre，平时作业少',assessment:''}]).value,'none');
 assert.equal(presentationSignal([{teaching:'',workload:'一次小组pre和期末论文',assessment:''}]).value,'has');
});

test('“必须” excludes a section only on known contrary data; missing data stays neutral',()=>{
 const detail={sections:[],evidence:[{teacher:'甲',teaching:'',workload:'每节点名',assessment:''}]};
 const prefs={...defaultPrefs(),noRollcall:2,noMidterm:2};
 const strict=judgeSection(course,detail,sec('1','甲','1~16周 星期一 3~4节',A(50,20,10)),prefs);
 assert.deepEqual(strict.blocked.sort(),['不点名','没有期中'].sort());
 const unknown=judgeSection(course,{sections:[],evidence:[]},sec('2','乙','1~16周 星期一 3~4节',[]),prefs);
 assert.deepEqual(unknown.blocked,[]);
 assert.ok(unknown.checks.every(c=>c.status==='unknown'));
});

test('exam-weight direction, early classes and free days are scored from the timetable and assessment',()=>{
 const detail={sections:[],evidence:[]};
 const low={...defaultPrefs(),examWeight:1,examDirection:'low'},high={...low,examDirection:'high'};
 const light=sec('1','甲','1~16周 星期二 6~7节',A(30,0,10,60)),heavy=sec('2','乙','1~16周 星期二 6~7节',A(70,20,10));
 assert.ok(judgeSection(course,detail,light,low).score>judgeSection(course,detail,heavy,low).score);
 assert.ok(judgeSection(course,detail,heavy,high).score>judgeSection(course,detail,light,high).score);
 const time={...defaultPrefs(),noEarly:2,freeDays:2,freeDayList:[5]};
 assert.deepEqual(judgeSection(course,detail,sec('3','丙','1~16周 星期三 1~2节',A(50,0,10)),time).blocked,['不要早八']);
 assert.deepEqual(judgeSection(course,detail,sec('4','丁','1~16周 星期五 3~4节',A(50,0,10)),time).blocked,['空出周五']);
 assert.deepEqual(judgeSection(course,detail,sec('5','戊','1~16周 星期四 3~4节',A(50,0,10)),time).blocked,[]);
});

test('normal-class filter drops honours and talent sections, and term filter applies',()=>{
 const detail={sections:[sec('1','甲','1~16周 星期一 3~4节',A(50,0,10)),sec('2','乙','1~16周 星期一 3~4节',A(50,0,10),{class_type:'英才班'}),sec('3','丙','1~16周 星期一 3~4节',A(50,0,10),{term:'2025秋'})],evidence:[]};
 assert.deepEqual(rankTeachers(course,detail,defaultPrefs()).map(r=>r.section.id),['1']);
 assert.deepEqual(rankTeachers(course,detail,{...defaultPrefs(),normalOnly:false}).map(r=>r.section.id).sort(),['1','2']);
});

test('combination search trades a slightly worse teacher for a conflict-free timetable',()=>{
 const prefs={...defaultPrefs(),noRollcall:1};
 const c1={id:'X',name:'课一',code:'X'},c2={id:'Y',name:'课二',code:'Y'};
 const d1={sections:[sec('x1','甲','1~16周 星期一 3~4节',A(50,0,5)),sec('x2','乙','1~16周 星期二 3~4节',A(50,0,20))],evidence:[]};
 const d2={sections:[sec('y1','丙','1~16周 星期一 3~4节',A(50,0,0))],evidence:[]};
 const r=bestCombos([{course:c1,rows:rankTeachers(c1,d1,prefs)},{course:c2,rows:rankTeachers(c2,d2,prefs)}]);
 assert.equal(r.combos[0].missing.length,0);
 assert.deepEqual(r.combos[0].items.map(i=>i.row.section.id),['x2','y1']);
 // 避开课表里已有的课：周二被占后，课一只能空着
 const fixed=[{course:{id:'Z'},section:sec('z','己','1~16周 星期二 3~4节')}];
 const r2=bestCombos([{course:c1,rows:rankTeachers(c1,d1,prefs)},{course:c2,rows:rankTeachers(c2,d2,prefs)}],{fixed});
 assert.deepEqual(r2.combos[0].missing.map(c=>c.id),['X']);
 assert.equal(r2.combos[0].items.find(i=>i.course.id==='Y').row.section.id,'y1');
});

test('one-line request is parsed into courses and graded requirements on the real catalog',()=>{
 const r=parseRequest('数理统计、羽毛球，必须不点名，期末占比小，不要早八，周五空出来，不要pre',data.courses,{term:'2026春',details,plan:'152034'});
 assert.deepEqual(r.courses.map(c=>c.code).sort(),['GEEC10314','MATH30011']);
 assert.equal(r.prefs.noRollcall,2);
 assert.equal(r.prefs.examWeight,1);assert.equal(r.prefs.examDirection,'low');
 assert.equal(r.prefs.noEarly,1);assert.equal(r.prefs.noPresentation,1);
 assert.deepEqual(r.prefs.freeDayList,[5]);
 const amb=parseRequest('数理统计',data.courses,{term:'2026春',details});
 assert.equal(amb.courses.length,0);
 assert.ok(amb.ambiguous[0].options.some(o=>o.code==='MATH30011'));
 assert.ok(matchCourse('MATH30011',data.courses,{term:'2026春',details}).exact);
 const exam=parseRequest('线性代数，考试占比大，周三和周五没课',data.courses,{term:'2026春',details});
 assert.equal(exam.prefs.examDirection,'high');assert.deepEqual(exam.prefs.freeDayList,[3,5]);
});

test('stored preferences are sanitised',()=>{
 const p=cleanPrefs({noRollcall:9,term:'<script>',freeDayList:[0,3,3,8,'5'],examDirection:'x',apiKey:'secret'});
 assert.equal(p.noRollcall,0);assert.equal(p.term,'2026春');assert.deepEqual(p.freeDayList,[3,5]);assert.equal(p.examDirection,'low');assert.equal('apiKey' in p,false);
});

test('every real course can be ranked, and combos on real data never overlap',()=>{
 const prefs={...defaultPrefs(),noRollcall:1,examWeight:1,noEarly:1,noPresentation:1,openBook:1,noPaper:1,lightHomework:1,noEvening:1,hasReviews:1,noMidterm:1};
 let ranked=0;
 for(const c of data.courses){const rows=rankTeachers(c,details[c.id],prefs);ranked+=rows.length;for(const r of rows)assert.ok(Number.isFinite(r.score));}
 assert.ok(ranked>5000);
 const offered=data.courses.filter(c=>(details[c.id]?.sections||[]).filter(s=>s.term==='2026春').length>=3);
 let seed=7;const rnd=()=>(seed=(seed*1103515245+12345)%2147483648)/2147483648;
 for(let trial=0;trial<25;trial++){
  const pickSet=[...new Set(Array.from({length:5},()=>offered[Math.floor(rnd()*offered.length)]))];
  const {combos}=bestCombos(pickSet.map(c=>({course:c,rows:rankTeachers(c,details[c.id],prefs)})));
  for(const combo of combos){
   const slots=combo.items.filter(i=>i.row).map(i=>parseSchedule(i.row.section.schedule).slots);
   for(let i=0;i<slots.length;i++)for(let j=i+1;j<slots.length;j++)assert.ok(!slots[i].some(a=>slots[j].some(b=>overlap(a,b))),'combo has a clash');
  }
 }
});
