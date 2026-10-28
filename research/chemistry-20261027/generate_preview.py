from pathlib import Path
import json,html
from urllib.parse import quote
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/n).read_text(encoding="utf8"))
e=load("official_evidence.json"); ar=load("alias_registry.json"); review=load("public_web_reviews.json") if (P/"public_web_reviews.json").exists() else {"records":[]}
esc=lambda s:html.escape(str(s if s is not None else ""),quote=True)
aliases={x["code"]:x for x in ar["courses"]}; teachers={x["name"]:x for x in ar["teachers"]}
records={}
danke=load("danke_review_summaries.json") if (P/"danke_review_summaries.json").exists() else {"records":[]}
for r in danke.get("records",[]):
 if r.get("course_code") and r.get("reading_status")=="full_text_read": records.setdefault(r["course_code"],[]).append(r)
forum=load("forum_discussion_summaries.json") if (P/"forum_discussion_summaries.json").exists() else {"records":[]}
for r in forum.get("records",[]):
 if r.get("course_code") and r.get("reading_status") in ("read","read_relevant_thread"): records.setdefault(r["course_code"],[]).append(r)
for r in review.get("records",[]):
 if r.get("course_code") and r.get("reading_status") in ("read","read_relevant_thread"): records.setdefault(r["course_code"],[]).append(r)
resources=load("course_resources.json").get("resources",[]) if (P/"course_resources.json").exists() else []
synth=load("course_syntheses.json") if (P/"course_syntheses.json").exists() else {}
parts=[]
all_plan_names=sorted({r.get("plan_name") for c in e["courses"] for r in c.get("plan_refs",[]) if r.get("plan_name")})
all_types=sorted({(o.get("course_type") or {}).get("nameZh") for c in e["courses"] for o in c.get("offerings",[]) if isinstance(o.get("course_type"),dict) and o.get("course_type",{}).get("nameZh")})
all_prefixes=sorted({"".join(ch for ch in c["code"] if ch.isalpha()).upper().removesuffix("H") for c in e["courses"]})
for c in e["courses"]:
 code=c["code"]; name=c["name"]; people=c["teachers"]; a=aliases.get(code,{})
 search=[code,name,*people]+[x["value"] for x in a.get("aliases",[]) if x.get("kind") in ("pinyin","pinyin_initials")]
 for t in people:
  if t in teachers:search += [teachers[t].get("pinyin",""),teachers[t].get("initials","")]
 credits_summary=sorted({o.get("credits") for o in c.get("offerings",[]) if o.get("credits") is not None})
 credits_label=" / ".join(str(x) for x in credits_summary)+" 学分" if credits_summary else "学分未提供"
 sections=[]
 for o in c["offerings"]:
  tt="、".join(o.get("teachers") or []) or "教师待确认"; limit=o.get("student_count"); credits=o.get("credits")
  typ=o.get("course_type") or {}; typ=typ.get("nameZh", "未提供") if isinstance(typ,dict) else typ
  sections.append(f'<li>{esc(o.get("term"))} · {esc(o.get("section_code"))} · {esc(tt)} · {esc(credits)} 学分 · {esc(typ)} · 选课人数快照 {esc(limit if limit is not None else "未提供")} · 大纲 {esc(o.get("syllabus_status"))}</li>')
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
   label="蛋壳课评 #"+str(r.get("source_ids",{}).get("review_id","")); mapping={"assigned_historical":"历史同名旧课号", "assigned_cross_department_same_code":"其他院系同课号", "assigned":"现行课号"}.get(r.get("course_mapping_status"),"课程对应待核"); kind={"brief_opinion":"简短评价", "experience_with_hearsay_claims":"含转述", "observer_or_hearsay_about_other_section":"对其他班观察", "low_information_opinion":"信息较少", "course_experience_or_assessment":"修读体验"}.get(r.get("review_type"),"学生评价"); teacher="、".join(r.get("teacher",[])) or "教师未注明";term=r.get("term") or "学期未注明";summary=r.get("paraphrase","")
   reviews.append(f'<article><p>{esc(summary)}</p><small>{esc(label)} · {esc(teacher)} · {esc(term)} · {esc(mapping)} · {esc(kind)}</small></article>')
  elif r.get("source_type")=="forum_discussion":
   reviews.append(f'<article><p>{esc(r.get("summary",""))}</p><small>树洞 #{esc(r.get("source_ids",{}).get("hole_id"))} · {esc(r.get("kind","讨论"))} · {esc(r.get("term",""))}</small></article>')
  elif r.get("source_type") in ("教师教学研究论文", "院系课程评估报道", "官方历史课程报道"):
   reviews.append(f'<article><p>{esc(r.get("summary",""))}</p><small>{esc(r.get("source_label",""))} · {esc(r.get("term",""))} · 历史课程族资料；非学生课评</small></article>')
  elif r.get("source_type")=="复旦大学化学系官方报道":
   reviews.append(f'<article><p>{esc(r.get("summary",""))}</p><small>来源：院系官方人物报道 · 课程族线索，荣誉版本及修读学期未核</small></article>')
  else:
   url=esc(r.get("source_url","")); label=esc(r.get("source_label","")); summary=esc(r.get("summary",""));term=esc(r.get("term",""));
   platform='小红书' if '小红书' in r.get('source_type','') else '知乎'; note='；帖子教师姓名与教务记录字形不同' if r.get('record_id')=='CHEM-WEB-XHS-0003' else ('；未答问课' if r.get('record_type')=='course_question' else ('；选课建议，未确认亲修' if r.get('record_type') in ('anonymous_course_selection_advice','anonymous_course_discussion') else ('；个人成绩自述' if r.get('record_type')=='first_person_grade_report' else '')))
   titles={'6a9f79c1000000001103670c':'复旦选课二选一','68aea713000000001d000597':'复旦化学系选课推荐','69b0261c000000001b01dd1c':'复旦化学系大二 Ask me anything'}
   title=next((t for k,t in titles.items() if k in url),None)
   if title:
    search_url='https://www.xiaohongshu.com/search_result?keyword='+quote(title)
    links=f'<a href="{url}" target="_blank" rel="noopener noreferrer">原帖直链</a> · <a href="{esc(search_url)}" target="_blank" rel="noopener noreferrer">在小红书搜索标题</a><small>（直链在 Edge 测试受平台限制；搜索结果可找到原帖）</small>'
   else:links=f'<a href="{url}" target="_blank" rel="noopener noreferrer">查看{platform}原文</a>'
   reviews.append(f'<article><p>{summary}</p><small>{label} · {term}{note}</small><br>{links}</article>')
 has_student_content=any((r.get("source_type") in ("danke_group_review", "forum_discussion") and r.get("has_student_review", True)) or (r.get("source_type") in ("知乎回答", "小红书笔记评论区", "小红书公开笔记评论") and r.get("has_student_review", True) and r.get("record_type") not in ("course_question", "course_selection_question", "first_person_grade_report")) for r in records.get(code,[]))
 if not has_student_content:
  reviews.insert(0,"<p>暂未收录可确认对应本课程的修读评价。已收录的问课、成绩自述与官方信息会单独标明。</p>")
 materials=[r for r in resources if code in r.get("course_codes",[])]
 links="".join(f'<article><a href="{esc(r["url"])}" target="_blank" rel="noopener noreferrer">{esc(r["title"])}</a><p>{esc(r["source"])} · {esc(r["note"])}</p></article>' for r in materials)
 plans=sorted(set(x.get("plan_name","")+" / "+x.get("module_name","") for x in c.get("plan_refs",[])))
 plan_names=sorted(set(x.get("plan_name","") for x in c.get("plan_refs",[]) if x.get("plan_name")))
 type_names=sorted({(o.get("course_type") or {}).get("nameZh") for o in c.get("offerings",[]) if isinstance(o.get("course_type"),dict) and o.get("course_type",{}).get("nameZh")})
 prefix="".join(ch for ch in code if ch.isalpha()).upper().removesuffix("H")
 honor='<span class="honor">荣誉课 · 优秀率比例不限</span>' if code.lower().endswith("h") else ""
 review_badge=' <span class="missing">暂未收录修读评价</span>' if not has_student_content else ""
 parts.append(f'''<details class="course" data-search="{esc(" ".join(search).lower())}" data-plans="{esc(json.dumps(plan_names,ensure_ascii=False))}" data-types="{esc(json.dumps(type_names,ensure_ascii=False))}" data-prefix="{esc(prefix)}"><summary><strong>{esc(name)}</strong> <span>{esc(code)} · {esc("、".join(c["terms"]))}</span><p>{esc("、".join(people))} · {esc(c["department"])} · {esc(credits_label)}</p>{honor}{review_badge}</summary><div class="inner"><h3>教学班与培养方案</h3><ul>{"".join(sections)}</ul><details><summary>方案课程位置（公共方案与所选专业方案合读）</summary><ul>{"".join("<li>"+esc(x)+"</li>" for x in plans) or "<li>未在本次方案列表中找到直接课号</li>"}</ul></details><h3>一、大纲</h3>{"".join(docs) or "<p>本次相关班次未取得可用大纲。</p>"}<h3>二、课程资料</h3>{links or "<p>资料检索与核对进行中。</p>"}<h3>三、学生评价与讨论</h3>{"".join(reviews) or "<p>学生评价检索和阅读进行中。</p>"}<h3>四、综合比较</h3><p>{esc(synth.get(code,{}).get("text","待学生评价、教学班和资料核实后补充。"))}</p></div></details>''')
page='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>化学系课程研究预览</title><style>body{{font:16px/1.65 system-ui,sans-serif;background:#f5f7f4;color:#203a33;margin:0}}main{{max-width:1080px;padding:24px;margin:auto}}input{{width:100%;box-sizing:border-box;padding:14px;border:1px solid #aac1b4;border-radius:10px;font:inherit}}.filters{{display:flex;gap:12px;flex-wrap:wrap}}.filters label{{display:flex;flex-direction:column;gap:4px;flex:1 1 200px}}select{{font:inherit;padding:9px;border:1px solid #aac1b4;border-radius:8px;background:white;max-width:100%}}.notice,.course{{background:white;border:1px solid #d9e2dd;border-radius:12px;padding:18px;margin:14px 0}}.notice{{border-left:5px solid #387d6d}}.course[data-prefix="CHEM"]{{border-left:5px solid #237e73}}.course[data-prefix="AIS"],.course[data-prefix="AIT"]{{border-left:5px solid #5950b6}}.course[data-prefix="GECC"]{{border-left:5px solid #c77d2b}}.course[data-prefix="GEEC"]{{border-left:5px solid #b4536e}}.course[data-prefix="GEIN"]{{border-left:5px solid #3287a4}}.course[data-prefix="GESP"]{{border-left:5px solid #a55c58}}.honor{{display:inline-block;color:#644396;background:#f0e9fa;border-radius:6px;padding:2px 8px}}.missing{{display:inline-block;color:#725b39;background:#f5eee3;border-radius:6px;padding:2px 8px}}summary{{cursor:pointer}}.course>summary strong{{font-size:21px}}.course>summary span,small{{color:#607c71}}.course>summary p{{margin:4px 0}}.inner{{border-top:1px solid #e6ede8;padding-top:8px}}.para{{white-space:pre-wrap}}article{{border-left:3px solid #8ab7a0;padding-left:14px}}h3{{margin-top:25px}}a{{color:#146b59}}</style></head><body><main><h1>化学系课程研究预览</h1><div class="notice">研究进行中：范围为 2025 秋与 2026 春化学系开课的 145 个课程代码。大纲、已核读评价及班次来源分开呈现，尚未检索完毕的课程不会误标为没有评价。人数为查询时快照。</div><label for="q">搜索课程代码、课程名、教师名或拼音首字母</label><input id="q" autocomplete="off" placeholder="例如 CHEM20001、分析化学、雷杰、lj"><p>培养方案按公共方案加所选专业方案合并筛选。</p><div class="filters"><label>培养方案 <select id="plan"><option value="">全部方案</option>__PLAN_OPTIONS__</select></label><label>课程类型 <select id="type"><option value="">全部类型</option>__TYPE_OPTIONS__</select></label><label>课程代码前缀 <select id="prefix"><option value="">全部前缀</option>__PREFIX_OPTIONS__</select></label></div><p id="count"></p><div id="courses">{}</div></main><script>const q=document.getElementById('q'),plan=document.getElementById('plan'),type=document.getElementById('type'),prefix=document.getElementById('prefix'),cards=[...document.querySelectorAll('.course')],count=document.getElementById('count');function filter(){{let v=q.value.trim().toLowerCase(),n=0;for(const c of cards){{let plans=JSON.parse(c.dataset.plans),types=JSON.parse(c.dataset.types),planOk=!plan.value||plans.includes(plan.value)||(plan.value!=='2026级 公共方案'&&plans.includes('2026级 公共方案'));let ok=(!v||c.dataset.search.includes(v))&&planOk&&(!type.value||types.includes(type.value))&&(!prefix.value||c.dataset.prefix===prefix.value);c.hidden=!ok;if(ok)n++}}count.textContent='显示 '+n+' / '+cards.length+' 门课程'}}q.addEventListener('input',filter);for(const x of [plan,type,prefix])x.addEventListener('change',filter);filter();</script></body></html>'''
option=lambda x:f'<option value="{esc(x)}">{esc(x)}</option>'
rendered=page.format(''.join(parts)).replace('__PLAN_OPTIONS__',''.join(option(x) for x in all_plan_names)).replace('__TYPE_OPTIONS__',''.join(option(x) for x in all_types)).replace('__PREFIX_OPTIONS__',''.join(option(x) for x in all_prefixes))
(P/'化学系课程研究预览.html').write_text(rendered,encoding='utf8')
print('Wrote',len(parts),'courses with',sum(len(x) for x in records.values()),'read source summaries/discussions')
