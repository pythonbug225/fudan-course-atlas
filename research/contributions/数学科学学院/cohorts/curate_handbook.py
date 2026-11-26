"""Keep a reviewable transcription of selected preparation statements."""
import json
from pathlib import Path
W=Path(__file__).resolve().parent;O=W if (W/'2023/official').exists() else W/'package/cohorts'
p=O/'sources/handbook-course-requirements.json';d=json.loads(p.read_text('utf-8'));rules=[]
def add(target,code,page,wording,antecedents,interpretation='手册大纲将前者列为预修、前续课程或应具备的知识基础。'):
 wording=wording.rstrip('。.')
 for source in antecedents:
  rules.append({'from':source,'to':target,'target_code':code,'pdf_pages':[page],'wording':wording,'interpretation':interpretation})
add('高等代数II','MATH130002',60,'已选修过高等代数I',['高等代数Ⅰ'])
add('常微分方程','MATH130183',68,'它的前续课程包括数学分析、高等代数、解析几何、普通物理等课程。',['解析几何'])
add('数学模型','MATH130008',91,'要求学生已具备数学分析、高等代数、常微分方程、初等概率论等数学基础',['常微分方程'])
add('数理方程','MATH130012',98,'本课程需要有数学分析、高等代数、复变函数、实变函数、泛函分析和常微分方程的知识。',['复变函数','实变函数','泛函分析','常微分方程'])
add('数理方程(H)','MATH130012h',191,'本课程需要有数学分析、高等代数、复变函数、实变函数、泛函分析和常微分方程的知识。',['复变函数','实变函数','泛函分析','常微分方程'])
add('微分方程数值解法','MATH130016',104,'预修课程：数值逼近、数值代数、常微分方程、数学物理方程',['数值逼近','数值代数','常微分方程'])
add('数理统计','MATH130060',134,'先修《数学分析》和《高等代数》，会R或其它相关编程语言。',[], '宽泛系列与编程能力保留原文，不展开成所有分析/代数课程必修链。')
add('统计中的计算方法','MATH130099',150,'预修课程包括：数学分析、高等代数、概率论、数理统计、数值计算。另外具备一定编程能力或者对编程有兴趣。',['概率论','数理统计'])
add('反问题的模型与计算','MATH130104',153,'预修课程: 偏微分方程、数值方法、数值代数、微分方程数值解、数学模型',['数值代数','数学模型'])
add('最优控制理论','MATH130039',159,'学生在学习本课程之前应已较好地掌握了数学分析、线性代数、常微分方程、实变函数和泛函分析等数学课程的基础知识。',['常微分方程','实变函数','泛函分析'])
add('泛函分析(H)','MATH130011h',188,'学习过数学专业的分析课程: 数学分析I-III(或高等数学上下+数学分析原理)、实变函数、复变函数，并取得良好成绩',['实变函数','复变函数'])
add('代数拓扑与微分形式(H)','MATH130144h',199,'预修: 微分流形，抽象代数',['微分流形','抽象代数'])
add('黎曼几何初步(H)','MATH130145h',201,'预修: 《曲线曲面论》（大学微分几何）、《点集拓扑》、《微分流形》',['微分流形'])
add('数学控制论(H)','MATH130164h',204,'学生在学习本课程之前应已较好地掌握了数学分析、线性代数、常微分方程、实变函数和泛函分析、概率论等数学课程的基础知识。',['常微分方程','实变函数','泛函分析','概率论'])
add('数值代数与优化(H)','MATH130165h',206,'学生在学习本课程之前应已较好的掌握了数学分析、线性代数、常微分方程、概率论和数值代数等数学课程。',['常微分方程','概率论','数值代数'])
add('表示论基础(H)','MATH130194h',211,'预修: 高等代数，数学分析，抽象代数',['抽象代数'])
add('交换代数(H)','MATH130195h',213,'预修: 高等代数，抽象代数、表示论',['抽象代数'])
add('同调代数(H)','MATH130196h',215,'预修：抽象代数和交换代数',['抽象代数'])
# Do not silently resolve generic “表示论”“交换代数” to a particular honors code.
# Those broad topics remain in the original requirement record.
d['curated_preparation']=rules
d['curation_note']='逐条选取可明确匹配的课程题名。手册泛称数学分析/高等代数等宽泛基础不自动展开为一串课；表示论、交换代数未擅自替换为当前荣誉课代码。未建立关系不代表没有知识准备要求。'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n','utf-8')
print('curated preparation statements',len(rules))
