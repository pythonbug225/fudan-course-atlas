"""Verify official catalogue completeness, source identities and byte integrity."""
import gzip,hashlib,json,zipfile
from pathlib import Path
W=Path(__file__).resolve().parent;ROOT=W.parent
def read(p):return json.loads(p.read_text('utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 historic=read(ROOT/'catalogue-evidence/directory-foreign-all-years.json')
 assert len(historic['data'])==historic['_page_']['totalRows']==456
 results=[]
 for year in (2023,2024,2025):
  root=ROOT/str(year)/'official';plans=read(root/'programmes.json')
  allpages=read(root/'raw/directory-all.json');deptpages=read(root/'raw/directory-department-2551.json')
  allrows=[row for page in allpages for row in page['response']['data']]
  deptrows=[row for page in deptpages for row in page['response']['data']]
  assert len(allrows)==allpages[0]['response']['_page_']['totalRows']
  assert len(deptrows)==deptpages[0]['response']['_page_']['totalRows']
  selected={r['ID']for r in allrows if r.get('DEPART_IDS')==2551}
  assert selected=={r['ID']for r in deptrows}=={r['ID']for r in historic['data']if r['YEARS']==str(year)}=={int(r['plan_id'])for r in plans}
  figure_count=0
  for p in plans:
   raw=root/p['raw_path'];assert sha(raw)==p['raw_sha256']
   response=gzip.decompress(raw.read_bytes());assert hashlib.sha256(response).hexdigest()==p['response_sha256']
   model=json.loads(response)['model'];assert str(model['id'])==p['plan_id'];assert str(model['grade'])==str(year);assert model['department']['id']==2551
   assert model['nameZh']==p['title']
   word=root/p['word_path'];assert sha(word)==p['word_sha256'];assert word.stat().st_size==p['word_bytes']
   with zipfile.ZipFile(word)as z:assert z.testzip()is None
   assert(root/p['word_text_path']).is_file()
   for image in p['images']:assert sha(root/image['path'])==image['sha256'];figure_count+=1
  results.append({'cohort':year,'all_department_directory_count':len(allrows),'department_plans':len(plans),'raw_json_verified':len(plans),'word_originals_verified':len(plans),'embedded_images_verified':figure_count,'catalogue_cross_checks':['year-only all departments','year + department 2551','department 2551 all years'],'metadata_and_hashes_valid':True})
 report={'checked_on':'2026-11-26','department':'外国语言文学学院','department_id':2551,'sources':results,'limitation':'此校验仅证实教务系统当前公开目录的完整下载；2023/2024目录部分专业缺列，须结合教务处历史PDF，不能推断未列专业当年不存在。公共方案独立接口需登录，专业JSON并非全部毕业要求。'}
 (ROOT/'source-download-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
