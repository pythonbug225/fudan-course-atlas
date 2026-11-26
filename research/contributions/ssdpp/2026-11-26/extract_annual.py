"""Extract 2024 official annual-book sections, preserving original table cells."""
import hashlib,json,re,sys
from pathlib import Path
import pdfplumber,pymupdf
W=Path(__file__).resolve().parent
R=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else W/'2024/official/annual'
R.mkdir(parents=True,exist_ok=True)
if len(sys.argv)<2:raise SystemExit('Usage: python extract_annual.py ORIGINAL_2024_PDF [OUTPUT_DIRECTORY]')
F=Path(sys.argv[1]).resolve()
assert hashlib.sha256(F.read_bytes()).hexdigest()=='5d01aacebcd38b41d4ca237c58698270a9e07cf9198502d8265b6d8b8f94a215','Unexpected source PDF: review edition before extraction'
URL='https://jwc.fudan.edu.cn/_upload/article/files/83/6c/8a3c080c4f8991024f4b59ad4f1b/a5fbd7c6-a589-4638-a379-cc2297ca3ea6.pdf'
def save(p,d):p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
sections=[{'id':'annual2024-sociology','major':'社会学','pages':list(range(377,385)),'body_pages':list(range(377,381))}, {'id':'annual2024-social-work','major':'社会工作','pages':list(range(385,392)),'body_pages':[385,386,387]}, {'id':'annual2024-psychology','major':'心理学','pages':list(range(747,754)),'body_pages':[747,748,749]}]
codepat=re.compile(r'[A-Z]{2,}\d{5,}[hH]?')
d=pymupdf.open(F);texts={};tables=[];courses=[];issues=[]
with pdfplumber.open(F) as pdf:
 for sec in sections:
  prev_scope='方案专业课程';prev_module='专业课程'
  for page_no in sec['pages']:
   page=pdf.pages[page_no-1];text=d[page_no-1].get_text();texts[str(page_no)]={'printed_page':page_no-14,'text':text}
   if '修读建议（留学生适用）' in text[:160]:prev_scope='留学生修读建议'
   elif '修读建议' in text[:160]:prev_scope='普通修读建议'
   for ti,table in enumerate(page.find_tables()):
    raw=table.extract();table_id=f'p{page_no}-t{ti}';tables.append({'id':table_id,'page':page_no,'rows':raw})
    header=raw[0];codecol=next((i for i,x in enumerate(header) if x and '课程代码' in x.replace('\n','')),None)
    if codecol is None:issues.append({'page':page_no,'table':ti,'reason':'header_missing'});continue
    namecol=next((i for i,x in enumerate(header) if x and ('课程名称' in x.replace('\n','') or '课程/模块名称' in x.replace('\n',''))),None)
    if namecol is None:issues.append({'page':page_no,'table':ti,'reason':'name_header_missing'});continue
    for ri,row in enumerate(raw[1:],1):
     if prev_scope!='方案专业课程' and len(row)>3:
      if row[1]:prev_module=row[1].replace('\n','')
     if codecol>=len(row) or not row[codecol]:continue
     codes=codepat.findall(row[codecol]);names=(row[namecol] or '').splitlines()
     if not codes:continue
     # One code: concatenate wrapped title lines. Multi-line merged cell:
     # align wrapped titles to code y positions only when the line counts differ.
     if len(codes)==1:named=[(codes[0],''.join(names))]
     elif len(codes)==2 and len(names)==1 and '（上）、（下）' in names[0]:
      base=names[0].split('（上）')[0];named=[(codes[0],base+'（上）'),(codes[1],base+'（下）')]
     elif len(codes)==len(names):named=list(zip(codes,names))
     elif len(names)==1:named=[(c,names[0]) for c in codes]
     else:
      cb=table.rows[ri].cells[codecol];nb=table.rows[ri].cells[namecol]
      cw=[w for w in page.crop(cb).extract_words() if codepat.fullmatch(w['text'])]
      nw=page.crop(nb).extract_words();named=[]
      for ci,cw0 in enumerate(cw):
       mid=(cw0['top']+cw0['bottom'])/2
       lo=nb[1] if ci==0 else (mid+(cw[ci-1]['top']+cw[ci-1]['bottom'])/2)/2
       hi=nb[3] if ci==len(cw)-1 else (mid+(cw[ci+1]['top']+cw[ci+1]['bottom'])/2)/2
       name=''.join(w['text'] for w in nw if lo <=(w['top']+w['bottom'])/2<hi)
       named.append((cw0['text'],name))
      if len(named)!=len(codes):issues.append({'page':page_no,'row':ri,'codes':codes,'names':names,'reason':'alignment'});continue
     for code,name in named:
      assert name and code in text,(page_no,code,name)
      courses.append({'cohort':2024,'plan_id':sec['id'],'plan_title':'2024年度汇编／'+sec['major']+'专业','major':sec['major'],'module':prev_scope+'／'+(prev_module if prev_scope!='方案专业课程' else '专业课程表'),'course_code':code,'course_name':name.strip(),'pdf_page':page_no,'printed_page':page_no-14,'table_id':table_id,'table_row_index':ri,'raw_table_row':row,'population_scope':prev_scope,'edition':'2024年度汇编（原十位课程代码）'})
  # Extracted PDFs are derivatives; full byte original is in the Release.
  out=pymupdf.open();out.insert_pdf(d,from_page=sec['pages'][0]-1,to_page=sec['pages'][-1]-1)
  path=R/(sec['id']+'.pdf');out.save(path,garbage=4,deflate=True)
  sec['excerpt_path']=path.name;sec['excerpt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
save(R/'courses.json',courses);save(R/'tables.json',tables);save(R/'pages.json',texts)
save(R/'metadata.json',{'source_url':URL,'title':'复旦大学2024年本科教学培养方案','source_sha256':hashlib.sha256(F.read_bytes()).hexdigest(),'bytes':F.stat().st_size,'pages':len(d),'cohort_verified_at_pdf_page':15,'year_evidence':'2024 年“2+X”本科教学培养方案已覆盖全校绝大多数院系专业','retrieved_on':'2026-11-26','sections':sections,'extraction_issues':issues})
(R/'year-proof-page-15.txt').write_text(d[14].get_text(),encoding='utf-8')
print(json.dumps({'rows':len(courses),'codes':len({c['course_code'] for c in courses}),'issues':issues,'sections':[{'id':s['id'],'rows':sum(c['plan_id']==s['id'] for c in courses)} for s in sections]},ensure_ascii=False))
