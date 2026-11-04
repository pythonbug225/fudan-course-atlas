const assert=require('assert/strict'),fs=require('fs');
const root=require('path').join(__dirname,'..','public');
const vm=require('node:vm');const box={module:{exports:{}}};vm.runInNewContext(fs.readFileSync(root+'/assets/components.js','utf8'),box);const t=box.module.exports,p=require('../scripts/read-catalog.cjs')(root+'/data/grading.json'),f=require('../scripts/read-catalog.cjs')(root+'/data/fitness.json');
let passed=0;function near(a,b){assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);passed++}
let r=t.multiGPA({gpa:3.6,credits:60},[{credits:3,grade:'A-'},{credits:2,grade:'B+'},{credits:4,grade:'P'},{credits:2,grade:'NP'}],p);
near(r.low,(216+11.1+6.6)/65);near(r.high,(216+11.4+7.2)/65);near(r.excluded,6);near(r.denominator,65);
r=t.multiGPA({gpa:0,credits:0},[{credits:3,grade:'F'}],p);near(r.low,0);near(r.denominator,3);
assert.throws(()=>t.multiGPA({gpa:3.6,credits:60},[{credits:0,grade:'A'}],p));passed++;
r=t.mapRawScore(88,'A 90\nA- 85\nB+ 80\nF 0','88 88 86 85 93 79',p);assert.equal(r.grade,'A-');near(r.low,3.775);assert.equal(r.n,3);passed++;
assert.throws(()=>t.mapRawScore(88,'A 90\nA- 85\nF 0','87 85',p));passed++;
assert.throws(()=>t.parseThresholds('A 80\nB 90',p));passed++;
near(t.parseRun('3:17'),197);near(t.parseRun('3分17秒'),197);near(t.parseRun('197秒'),197);assert.throws(()=>t.parseRun('3.17'));passed++;assert.throws(()=>t.parseRun('3:65'));passed++;
for(const sex of ['male','female'])for(const year of ['12','34']){
 const g=f.groups[sex+'_'+year],full=g.rows[0],input={sex,year,height:170,weight:60,...full,run:full.run+'秒'};
 r=t.fitnessResult(input,f);near(r.total,100);near(r.strengthBonus,0);near(r.runBonus,0);
 r=t.fitnessResult({...input,strength:full.strength+g.bonus[0].strength_extra,run:(full.run-g.bonus[0].run_seconds_faster)+'秒'},f);near(r.total,120);
 for(const row of g.rows)for(const key of ['lung','sprint','reach','jump','strength','run'])if(row[key]!==null){near(t.thresholdScore(g,key,row[key]),row.points)}
}
near(t.thresholdScore(f.groups.male_12,'strength',14),76);near(t.thresholdScore(f.groups.male_12,'strength',4),0);near(t.thresholdScore(f.groups.male_12,'run',200),95);
assert.throws(()=>t.fitnessResult({sex:'male',year:'12',height:'',weight:60},f));passed++;
console.log(JSON.stringify({passed}));
