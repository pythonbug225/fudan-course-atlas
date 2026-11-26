"""Extract requirement fields within each syllabus, without borrowing next-page entries.

Requires PyMuPDF. The reviewed 68-entry title index accompanies the source PDF.
Run curate_handbook.py afterwards to restore the separately reviewed relation recipes.
"""
import hashlib,json,re
from pathlib import Path
import pymupdf
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts';S=O/'sources'
pdf=S/'math-handbook-2024.pdf';doc=pymupdf.open(pdf);pages=[p.get_text() for p in doc]
entries=json.loads((S/'handbook-index.json').read_text('utf-8'));full='';offsets=[]
for text in pages:offsets.append(len(full));full+=text+'\n'
positions=[]
for c in entries:
 page=c['pdf_page'];offset=pages[page-1].find(c['old_code']);assert offset>=0
 positions.append(offsets[page-1]+offset)
assert positions==sorted(positions) and len(entries)==68
records=[]
for i,c in enumerate(entries):
 a=positions[i];b=positions[i+1] if i+1<len(positions) else len(full);segment=full[a:b];req=[]
 for match in re.finditer(r'(?:基本要求\s*[:：]?|预修课程(?:及\s*其他要求)?)',segment):
  tail=segment[match.end():];stop=re.search(r'授课方式|主讲教师|课程负责人|教学目的|教学团队|教学内容安排|教材（|教材\(',tail)
  text=(tail[:stop.start()] if stop else tail[:800]).strip()
  if text and len(text)<1800:
   pos=a+match.start();page=max(j+1 for j,v in enumerate(offsets) if v<=pos)
   req.append({'pdf_page':page,'text':text})
 records.append(c|{'syllabus_pdf_pages':[c['pdf_page'],entries[i+1]['pdf_page'] if i+1<len(entries) else 217],'requirements':req})
p=S/'handbook-course-requirements.json';previous=json.loads(p.read_text('utf-8'))
previous.update({'courses':records,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'extraction_note':'按完整大纲的标题至下一大纲标题切分，跳过专业进阶目录的重复交叉引用。基本要求同时含学习成果和行为要求，不全部认定为先修。'})
p.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n','utf-8')
print('extracted',len(records),'syllabuses')
