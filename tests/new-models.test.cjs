const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.join(__dirname,'..','public'),box={module:{exports:{}}};vm.runInNewContext(fs.readFileSync(root+'/assets/components.js','utf8'),box);const t=box.module.exports,p=require('../scripts/read-catalog.cjs')(root+'/data/grading.json');let passed=0;
const near=(a,b)=>{assert.ok(Math.abs(a-b)<1e-9,`${a} != ${b}`);passed++};const base={allCredits:0,allGpa:0,professionalCredits:0,professionalGpa:0};
let rows=[{credits:3,grade:'A+',professional:true},{credits:2,grade:'B',professional:false}];let r=t.collegeGPA(base,rows,p,{correction:0});near(r.all.low,3.78);near(r.professional.low,4.3);near(r.low,4.04);near(r.high,4.08); // B为3.0—3.2，未知实际值保留区间。
r=t.multiGPA({credits:0,gpa:0},[{credits:3,grade:'A+'},{credits:2,grade:'manual',manual:3}],p);near(r.low,3.6);
rows=[{credits:3,grade:'A-',manual:3.775,professional:true},{credits:2,grade:'A',professional:false}];r=t.collegeGPA(base,rows,p,{correction:0});near(r.low,3.82);near(r.high,3.82);near(r.low/4.3*70,62.1860465116279);
r=t.collegeGPA(base,rows,p,{correction:0,fixed:true});near(r.low,3.76);near(r.high,3.76);
r=t.collegeGPA(base,[...rows,{credits:8,grade:'NP',professional:true}],p,{correction:.3});near(r.allCredits,5);near(r.professionalCredits,3);near(r.excluded,8);near(r.adjustedLow,3.52);
for(const [taken,required,expected] of [[0,20,.4],[4,20,.4],[5,20,.3],[9,20,.3],[10,20,.2],[14,20,.2],[16,20,0],[25,20,0]])near(t.mathCorrection(taken,required).correction,expected);
assert.equal(t.mathCorrection(15,20).correction,null);passed++;near(t.mathCorrection(15,20,'0').correction,0);near(t.mathCorrection(15,20,'.2').correction,.2);
assert.throws(()=>t.collegeGPA(base,[{credits:3,grade:'A-',manual:3.9,professional:true}],p));passed++;
const bands=[[0,59,'F',0],[60,61,'D',1.3],[62,65,'C-',1.7],[66,70,'C',2],[71,74,'C+',2.3],[75,77,'B-',2.7],[78,81,'B',3],[82,84,'B+',3.3],[85,89,'A-',3.7],[90,100,'A',4]];
for(let score=0;score<=100;score++){const e=bands.find(b=>score>=b[0]&&score<=b[1]),v=t.peMap(score);assert.equal(v.grade,e[2]);near(v.point,e[3]);}
near(t.peMap(89.5).point,3.7);near(t.peMap(60,'makeup').point,1);near(t.peMap(59,'makeup').point,0);assert.equal(t.peMap(60,'pnp').grade,'P');passed++;assert.equal(t.peMap(59,'pnp').grade,'NP');passed++;assert.equal(t.peMap(60,'pnp').point,null);passed++;
assert.throws(()=>t.peMap(101));passed++;assert.throws(()=>t.peMap(-1));passed++;
r=t.multiGPA({credits:0,gpa:0},[{credits:1,grade:'A-',peRequired:true}],p);near(r.low,3.7);near(r.high,3.7);
console.log(JSON.stringify({passed}));
