"""Extract exact survey rows and build a name-only pinyin search index."""
from pathlib import Path
import json,re,sys,unicodedata
from pypinyin import lazy_pinyin,Style
from PIL import Image
from catalog_io import read_catalog
ROOT=Path(__file__).resolve().parents[1]/'public'
def read(name):return read_catalog(ROOT/'data'/name)
def write(name,data):(ROOT/'data'/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
def norm(s):return re.sub(r'[\s·，,:：]','',unicodedata.normalize('NFKC',s).lower())
def initials(s,teacher=False):
 s=unicodedata.normalize('NFKC',s)
 letters=lazy_pinyin(s,style=Style.FIRST_LETTER,errors=lambda word:list(word))
 surname={'解':'x','单':'s','仇':'q','朴':'p','查':'z','区':'o','曾':'z','翟':'z','缪':'m','郇':'x','重':'c'}
 if teacher and s and s[0] in surname:letters[0]=surname[s[0]]
 return ''.join(letters).lower()
d=read('catalog.json');s=read('survey.json');notes={n['key']:n for n in d['notes']}
supplement=read('review-supplement.json') if (ROOT/'data/review-supplement.json').exists() else {'records':[]}
enrollment=read('enrollment.json') if (ROOT/'data/enrollment.json').exists() else {'records':[]}
handbooks=read('handbooks.json') if (ROOT/'data/handbooks.json').exists() else {'records':[]}
historical_teachers={};historical_sections={}
for r in enrollment['records']:
 for cid in r['course_ids']:
  historical_teachers.setdefault(cid,set()).update(r['teachers'])
  historical_sections.setdefault(cid,set()).update([r['section_code'],r['section_code'].split('.')[0]])
image=Image.open(ROOT/s['image']).convert('RGB');dest=ROOT/'assets/survey-rows';dest.mkdir(exist_ok=True)
name_map={'人工智能数学基础':'人工智能的数学基础','人工智能软件基础':'人工智能的软件基础','伦理':'人工智能的伦理与治理'}
for r in s['rows']:
 r['matched_course_name']=name_map.get(r['course'],r['course'])
 r['name_match_note']='按原图计算机课程分组和简称对照；原图未标教师，不对应某一任课教师。' if r['course']=='伦理' else '原图省略“的”字，按课程全名对照。' if r['course'] in name_map else ''
 r['course_ids']=[g['id'] for g in d['scope'] if norm(g['name'])==norm(r['matched_course_name'])]
 top=r['source_row']*30
 if not 30<=top<image.height-29:raise ValueError(r['id'])
 # Document extraction: keep the original header and full source row verbatim.
 crop=Image.new('RGB',(image.width,60),'white');crop.paste(image.crop((0,0,image.width,30)),(0,0));crop.paste(image.crop((0,top,image.width,top+30)),(0,30))
 crop.save(dest/(r['id']+'.png'),optimize=True);r['row_image']='assets/survey-rows/'+r['id']+'.png'
write('survey.json',s)
entries={}
for g in d['scope']:
 course_names=[g['name'],*d['course_aliases'].get(g['name'],[])]
 teacher_names=list(dict.fromkeys(g['teachers']+[t for k in g['note_keys'] for t in notes.get(k,{}).get('teachers',[])]+[t for r in s['rows'] if g['id'] in r['course_ids'] for t in r['teachers']]))
 teacher_names=list(dict.fromkeys(teacher_names+[t for r in supplement['records'] if g['id'] in r['course_ids'] for t in r.get('teacher_names',[]) if t]))
 teacher_names=list(dict.fromkeys(teacher_names+sorted(historical_teachers.get(g['id'],[]))))
 teacher_names=list(dict.fromkeys(teacher_names+[t for r in handbooks['records'] if g['id'] in r['course_ids'] for t in r.get('teacher_names',[])]))
 fields=[g['code'],*g.get('historical_codes',[]),*[o['code'] for o in g['offerings']]]
 fields.extend(sorted(historical_sections.get(g['id'],[])))
 for n in course_names:fields.extend([n,initials(n),re.sub(r'[^a-z0-9]','',initials(n))])
 for n in teacher_names:
  fields.extend([n,initials(n,True)])
  if n in d['aliases']:fields.append(d['aliases'][n])
  fields.extend(d.get('teacher_aliases',{}).get(n,[]))
 entries[g['id']]={'fields':list(dict.fromkeys(norm(x) for x in fields if x)),'teachers':teacher_names}
write('search.json',{'scope':'课程代码、课程名称、已知课程别名、相关教师姓名及拼音首字母；不含内部ID、分类与评论正文。','entries':entries})
print('SEARCH_AND_ROW_CROPS_READY',len(entries),'courses',len(s['rows']),'survey row images')
