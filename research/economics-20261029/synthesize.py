import json,re
from pathlib import Path
P=Path(__file__).resolve().parent
d=json.loads((P/'dataset.json').read_text('utf8'))
student=json.loads((P/'student_syntheses.json').read_text('utf8')) if (P/'student_syntheses.json').exists() else {}
def short(t,n=210):
 t=re.sub(r'\s+',' ',t).strip();parts=re.split(r'(?<=[。！？])',t);out=''
 for p in parts:
  if out and len(out)+len(p)>n:break
  out+=p
  if len(out)>=n:break
 return out if len(out)<n*2 else out[:n]+'…'
for c in d['courses']:
 docs=c['syllabi'];base=''
 if docs:
  p=next((p['content'] for p in docs[0]['paragraphs'] if p['heading'] in ('课程简介（中文）','课程简介','教学目标') and len(p['content'])>25),'')
  base=short(p)
  groups={}
  for doc in docs:
   a='、'.join(re.sub(r'[A-Za-z][A-Za-z ()-]*','',x.get('criteria','')).strip()+(f"{float(x['percentage']):g}%" if isinstance(x.get('percentage'),(float,int)) else '') for x in doc.get('assessment',[]) if x.get('criteria','').strip())
   if a:groups.setdefault(a,[]).append(doc['label'])
  if not any(x.get('criteria','').strip() for x in docs[0].get('assessment',[])):
   base+=' '+docs[0]['label']+'的考核比例栏未填写有效项目。'
  if len(groups)==1:
   labels=next(iter(groups.values()));base+=' '+('已取得的'+str(len(labels))+'份班次大纲考核一致：' if len(labels)>1 else labels[0]+'考核：')+next(iter(groups))+'。'
  elif groups:
   base+=' 平行班或学期之间的考核安排有差异：'+'；'.join('、'.join(v)+'为'+k for k,v in groups.items())+'。'
 else:
  credits=sorted({str(o['credits']) for o in c['offerings'] if o.get('credits') is not None})
  base=c['name']+'在这两学期共有'+str(len(c['offerings']))+'个教学班'+('，'+ '/'.join(credits)+'学分' if credits else '')+'。具体开课教师与人数见班次表；大纲获取状态逐班列出。'
 if c.get('honor'):base+=' 荣誉课优秀率比例不限。'
 addition=student.get(c['code'],{})
 text=addition.get('text','') if isinstance(addition,dict) else addition
 c['synthesis']=base+(' '+text if text else '')
 c['card_summary']=short(text if isinstance(addition,dict) and addition.get('source_ids') else base,180)
 c['synthesis_review_ids']=addition.get('source_ids',[]) if isinstance(addition,dict) else []
(P/'dataset.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf8')
