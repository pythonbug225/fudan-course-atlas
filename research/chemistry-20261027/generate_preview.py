from pathlib import Path
import json,html
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text(encoding="utf8"))
e=load("official_evidence.json"); ar=load("alias_registry.json"); review=load("public_web_reviews.json") if (P/"public_web_reviews.json").exists() else {"records":[]}
esc=lambda s:html.escape(str(s if s is not None else ""),quote=True)
aliases={x["code"]:x for x in ar["courses"]}; teachers={x["name"]:x for x in ar["teachers"]}
records={}
danke=load("danke_review_summaries.json") if (P/"danke_review_summaries.json").exists() else {"records":[]}
for r in danke.get("records",[]):
 if r.get("course_code") and r.get("reading_status")=="full_text_read": records.setdefault(r["course_code"],[]).append(r)
for r in review.get("records",[]):
 if r.get("course_code") and r.get("reading_status")=="read": records.setdefault(r["course_code"],[]).append(r)
synth=load("course_syntheses.json") if (P/"course_syntheses.json").exists() else {}
parts=[]
for c in e["courses"]:
 code=c["code"]; name=c["name"]; people=c["teachers"]; a=aliases.get(code,{})
 search=[code,name,*people]+[x["value"] for x in a.get("aliases",[]) if x.get("kind") in ("pinyin","pinyin_initials")]
 for t in people:
  if t in teachers:search += [teachers[t].get("pinyin",""),teachers[t].get("initials","")]
 sections=[]
 for o in c["offerings"]:
  tt="、".join(o.get("teachers") or []) or "教师待确认"; limit=o.get("student_count"); credits=o.get("credits")
  sections.append(f'<li>{esc(o.get("term"))} · {esc(o.get("section_code"))} · {esc(tt)} · {esc(credits)} 学分 · 选课人数快照 {esc(limit if limit is not None else "未提供")} · 大纲 {esc(o.get("syllabus_status"))}</li>')
 docs=[]
 for d in c["syllabus_documents"]:
  classes="；".join(str(x.get("term",""))+" "+str(x.get("section_code",""))+" "+"、".join(x.get("teachers",[])) for x in d.get("classes",[]))
  paras="".join(f'<h5>{esc(x.get("heading"))}</h5><p class="para">{esc(x.get("content"))}</p>' for x in d.get("paragraphs",[]) if x.get("content"))
  if not paras:continue
  ass="；".join(str(x.get("criteria",""))+" "+str(x.get("percentage",""))+"%" for x in d.get("assessment",[]))
  docs.append(f'<details><summary>查看大纲：{esc(classes)}</summary><p>考核：{esc(ass or "未提供")}</p>{paras}</details>')
 reviews=[]
 for r in records.get(code,[]):
  if r.get("source_type")=="danke_group_review":
   label="蛋壳课评 #"+str(r.get("source_ids",{}).get("review_id","")); mapping="历史同名旧课号" if r.get("course_mapping_status")=="assigned_historical" else "现行课号"; teacher="、".join(r.get("teacher",[])) or "教师未注明";term=r.get("term") or "学期未注明";summary=r.get("paraphrase","")
   reviews.append(f'<article><p>{esc(summary)}</p><small>{esc(label)} · {esc(teacher)} · {esc(term)} · {esc(mapping)}</small></article>')
  else:
   url=esc(r.get("source_url","")); label=esc(r.get("source_label","")); summary=esc(r.get("summary",""));term=esc(r.get("term",""));
   reviews.append(f'<article><p>{summary}</p><small>{label} · {term}</small><br><a href="{url}" target="_blank" rel="noopener noreferrer">查看知乎原文</a></article>')
 plans=sorted(set(x.get("plan_name","")+" / "+x.get("module_name","") for x in c.get("plan_refs",[])))
 parts.append(f'''<details class="course" data-search="{esc(" ".join(search).lower())}"><summary><strong>{esc(name)}</strong> <span>{esc(code)} · {esc("、".join(c["terms"]))}</span><p>{esc("、".join(people))} · {esc(c["department"])}</p></summary><div class="inner"><h3>教学班与培养方案</h3><ul>{"".join(sections)}</ul><details><summary>方案课程位置（公共方案与所选专业方案合读）</summary><ul>{"".join("<li>"+esc(x)+"</li>" for x in plans) or "<li>未在本次方案列表中找到直接课号</li>"}</ul></details><h3>一、大纲</h3>{"".join(docs) or "<p>本次相关班次未取得可用大纲。</p>"}<h3>二、课程资料</h3><p>资料检索与核对进行中。</p><h3>三、学生评价与讨论</h3>{"".join(reviews) or "<p>学生评价检索和阅读进行中。</p>"}<h3>四、综合比较</h3><p>{esc(synth.get(code,{}).get("text","待学生评价、教学班和资料核实后补充。"))}</p></div></details>''')
page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>化学系课程研究预览</title><style>body{{font:16px/1.65 system-ui,sans-serif;background:#f5f7f4;color:#203a33;margin:0}}main{{max-width:1080px;padding:24px;margin:auto}}input{{width:100%;box-sizing:border-box;padding:14px;border:1px solid #aac1b4;border-radius:10px;font:inherit}}.notice,.course{{background:white;border:1px solid #d9e2dd;border-radius:12px;padding:18px;margin:14px 0}}.notice{{border-left:5px solid #387d6d}}summary{{cursor:pointer}}.course>summary strong{{font-size:21px}}.course>summary span,small{{color:#607c71}}.course>summary p{{margin:4px 0}}.inner{{border-top:1px solid #e6ede8;padding-top:8px}}.para{{white-space:pre-wrap}}article{{border-left:3px solid #8ab7a0;padding-left:14px}}h3{{margin-top:25px}}a{{color:#146b59}}</style></head><body><main><h1>化学系课程研究预览</h1><div class="notice">研究进行中：范围为 2025 秋与 2026 春化学系开课的 145 个课程代码。大纲、已核读评价及班次来源分开呈现，尚未检索完毕的课程不会误标为没有评价。人数为查询时快照。</div><label for="q">搜索课程代码、课程名、教师名或拼音首字母</label><input id="q" autocomplete="off" placeholder="例如 CHEM20001、分析化学、雷杰、lj"><p id="count"></p><div id="courses">{}</div></main><script>const q=document.getElementById('q'),cards=[...document.querySelectorAll('.course')],count=document.getElementById('count');function filter(){{let v=q.value.trim().toLowerCase(),n=0;for(const c of cards){{let ok=!v||c.dataset.search.includes(v);c.hidden=!ok;if(ok)n++}}count.textContent='显示 '+n+' / '+cards.length+' 门课程'}}q.addEventListener('input',filter);filter();</script></body></html>'''
(P/'化学系课程研究预览.html').write_text(page.format(''.join(parts)),encoding='utf8')
print('Wrote',len(parts),'courses with',sum(len(x) for x in records.values()),'read review summaries')
