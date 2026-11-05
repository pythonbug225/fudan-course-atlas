import test from 'node:test';
import assert from 'node:assert/strict';
import {D1} from './helpers/d1.mjs';
import {createCompassSnapshot,activateCompassSnapshot,saveCompassSnapshot,getCompassSnapshot,parseCompassSnapshot,listCompassProfile} from '../lib/compass-state.ts';
const state=()=>({profile:{goal:'balanced',plan:'152034',term:'2026春',maxCredits:18,hours:30,freeWednesday:false,completed:[],englishTier:'B',development:'专业进阶路径',branches:{}},activeSlot:'A',records:[],recognitions:[],checks:{},allocations:{},planProfiles:{},plans:{A:[],B:[]}});
const create=async(db,label='A',importKey=null)=>createCompassSnapshot(db,'student',{label,source:'browser',importKey,state:state()});
test('snapshot creation, import deduplication, user isolation and stale versions',async()=>{
 const db=new D1(),a=await create(db,'A','fixture:import:1'),retry=await create(db,'A retry','fixture:import:1');
 assert.equal(a.created,true);assert.equal(retry.created,false);assert.equal(retry.snapshot.snapshotId,a.snapshot.snapshotId);
 assert.equal(await getCompassSnapshot(db,'another-user',a.snapshot.snapshotId),null);
 await activateCompassSnapshot(db,'student',a.snapshot.snapshotId,0);
 assert.equal((await saveCompassSnapshot(db,'student',a.snapshot.snapshotId,1,state())).version,2);
 await assert.rejects(()=>saveCompassSnapshot(db,'student',a.snapshot.snapshotId,1,state()),e=>e.status===409);
 await assert.rejects(()=>activateCompassSnapshot(db,'another-user',a.snapshot.snapshotId,0),e=>e.status===404);
 assert.equal((await listCompassProfile(db,'another-user')).snapshots.length,0);
});
test('a concurrent active-plan switch is rejected atomically without modifying the old snapshot',async()=>{
 const db=new D1(),a=(await create(db,'A')).snapshot,b=(await create(db,'B')).snapshot;
 await activateCompassSnapshot(db,'student',a.snapshotId,0);
 db.beforeRun=async(sql)=>{if(sql.startsWith('UPDATE compass_snapshots SET')){db.beforeRun=null;db.sql.prepare('UPDATE compass_profiles SET active_snapshot_id=?,version=version+1 WHERE user_id=?').run(b.snapshotId,'student');}};
 await assert.rejects(()=>saveCompassSnapshot(db,'student',a.snapshotId,1,{...state(),profile:{...state().profile,maxCredits:20}}),e=>e.status===409&&e.current.snapshotId===b.snapshotId&&e.profileVersion===2);
 assert.equal((await getCompassSnapshot(db,'student',a.snapshotId)).version,1);
 assert.equal((await getCompassSnapshot(db,'student',a.snapshotId)).state.profile.maxCredits,18);
});
test('switching away and back still rejects a save from the previous profile version',async()=>{
 const db=new D1(),a=(await create(db)).snapshot;await activateCompassSnapshot(db,'student',a.snapshotId,0);
 db.beforeRun=async(sql)=>{if(sql.startsWith('UPDATE compass_snapshots SET')){db.beforeRun=null;db.sql.prepare('UPDATE compass_profiles SET version=version+2 WHERE user_id=?').run('student');}};
 await assert.rejects(()=>saveCompassSnapshot(db,'student',a.snapshotId,1,state()),e=>e.status===409);
 assert.equal((await getCompassSnapshot(db,'student',a.snapshotId)).version,1);
});
test('cloud state rejects API keys and chats, and preserves two independent plans',()=>{
 assert.throws(()=>parseCompassSnapshot({...state(),checks:{deepseekKey:'fixture-not-a-real-key'}}));
 assert.throws(()=>parseCompassSnapshot({...state(),history:[]}));
 const input={...state(),plans:{A:[{course:'one',section:'a'}],B:[{course:'two',section:'b'}]}};
 const value=parseCompassSnapshot(input);assert.notDeepEqual(value.plans.A,value.plans.B);assert.equal('history' in value,false);
});
