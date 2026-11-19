"""Prepare local sources from the existing department download; no login/network."""
import pathlib,zipfile,json,xml.etree.ElementTree as E,hashlib,shutil
R=pathlib.Path(__file__).resolve().parent;S=R/'sources';S.mkdir(exist_ok=True)
archive=R.parent/'official/official-originals.zip';catalog=R.parent/'official/course_catalog.json'
if not archive.is_file() or not catalog.is_file():raise SystemExit('Download the whole journalism directory, including official/, before rebuilding.')
shutil.copy2(catalog,S/'course_catalog.json')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for f in z.namelist():
  p=S/'official'/f;assert p.resolve().is_relative_to((S/'official').resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(f))
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
(S/'figures').mkdir(exist_ok=True);ledger=[]
for f in (S/'official/official-word').glob('*.docx'):
 pid=f.name.split('_')[0]
 with zipfile.ZipFile(f) as z:
  rels={r.attrib['Id']:r.attrib['Target'] for r in E.fromstring(z.read('word/_rels/document.xml.rels'))};active=False;i=0
  for p in E.fromstring(z.read('word/document.xml')).findall('.//w:body/w:p',ns):
   text=''.join(p.itertext())
   if '课程体系与科研训练体系' in text:active=True
   elif active and '课程设置与修读要求' in text:active=False
   if active:
    for image in p.findall('.//a:blip',ns):
     rid=image.attrib['{'+ns['r']+'}embed'];b=z.read('word/'+rels[rid]);name=f'{pid}-{i}.png';(S/'figures'/name).write_bytes(b);ledger.append({'program':pid,'path':name,'relation_id':rid,'sha256':hashlib.sha256(b).hexdigest()});i+=1
(S/'figure-index.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Prepared 27 source programs and curriculum figures')
