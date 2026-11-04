const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),ts=require('typescript');
const root=path.resolve(__dirname,'..');
const file=path.join(root,'app/assets/[...path]/route.ts');
const output=ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText;
const api={};new Function('require','exports',output)(name=>name.endsWith('offsite-assets.json')?require('../public/data/offsite-assets.json'):require(name),api);
(async()=>{
for(const item of require('../public/data/offsite-assets.json').assets){
 for(const method of ['GET','HEAD']){
  const response=api[method](new Request('https://example.com/'+item.path+'?download=1',{method}));
  assert.equal(response.status,200);assert(response.headers.get('content-type').startsWith('text/html'));
  const body=await response.text();assert(body.includes('http-equiv="refresh"'));assert(body.includes(item.url));
 }
}
assert.equal(api.GET(new Request('https://example.com/assets/unknown.pdf')).status,404);
console.log('Published material URLs redirect to their exact preserved files; unknown paths stay 404.');

})().catch(error=>{console.error(error);process.exitCode=1});
