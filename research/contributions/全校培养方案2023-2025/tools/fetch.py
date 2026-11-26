"""Archive Fudan's public 2023–2025 plan listings, detail responses and verified Word originals."""
import argparse
import collections
import concurrent.futures as futures
import gzip
import hashlib
import http.client
import io
import json
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "https://fdjwgl.fudan.edu.cn/manager/bizType/2"
TODAY = time.strftime("%Y-%m-%d")
DATA = ROOT / "data"
DIRECTORY = ROOT / "directories"
YEARS = (2023, 2024, 2025)
CONNECTION = threading.local()

def put(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    temp.write_bytes(payload)
    os.replace(temp, path)

def write_json(path, data):
    put(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())

def sha(data):
    return hashlib.sha256(data).hexdigest()

def get(url, form=None):
    data = urllib.parse.urlencode(form).encode() if form else None
    headers = {"User-Agent": "Fudan-Course-Atlas-public-plan-archive/1", "Accept-Encoding": "gzip"}
    if form:headers["Content-Type"] = "application/x-www-form-urlencoded"
    for attempt in range(4):
        try:
            if attempt<3:
                target=urllib.parse.urlsplit(url)
                if not getattr(CONNECTION,"client",None):
                    CONNECTION.client=http.client.HTTPSConnection(target.hostname,timeout=50)
                CONNECTION.client.request("POST" if form else "GET",target.path+("?"+target.query if target.query else ""),body=data,headers=headers)
                with CONNECTION.client.getresponse() as response:
                    if response.status != 200:raise OSError(f"HTTP {response.status}")
                    body=response.read()
                    return gzip.decompress(body) if response.getheader("Content-Encoding")=="gzip" else body
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=50) as response:
                body=response.read()
                return gzip.decompress(body) if response.headers.get("Content-Encoding")=="gzip" else body
        except Exception:
            if getattr(CONNECTION,"client",None):
                CONNECTION.client.close()
                CONNECTION.client=None
            if attempt==3:
                raise
            time.sleep(1.5 * 2**attempt)

def directory(year):
    rows = []
    calls = []
    page = 1
    while True:
        query=urllib.parse.urlencode({"skipAuth":1,"YEARS":year,"queryPage__":f"{page},1000"})
        url=f"{BASE}/page-center/major-program-search-view/search?{query}"
        body=get(url)
        data=json.loads(body)
        total=int(data["_page_"]["totalRows"])
        rows.extend(data["data"])
        name=f"directory-{year}-p{page}.json.gz"
        archive=gzip.compress(body, compresslevel=5, mtime=0)
        put(DIRECTORY/name,archive)
        calls.append({"url":url,"file":name,"response_sha256":sha(body),"archive_sha256":sha(archive),"returned_rows":len(data["data"]),"total_rows":total})
        if len(rows)>=total:break
        if not data["data"]:raise ValueError("Unexpected empty page")
        page+=1
    if len(rows)!=total or len({r["ID"] for r in rows})!=total:raise ValueError("Directory count mismatch")
    if any(int(row["YEARS"])!=year for row in rows):raise ValueError("Incorrect directory year")
    return rows,calls

def normalized(text):
    return re.sub(r"\s+","",unicodedata.normalize("NFKC",text or ""))

def cached_sources():
    prior=collections.defaultdict(dict)
    for root in ROOT.parent.iterdir():
        if not root.is_dir() or root==ROOT:continue
        for base in [root/"package"/"cohorts",root/"package",root/"cohorts",root]:
            if not base.is_dir():continue
            for year in YEARS:
                official=base/str(year)/"official"
                for folder,pattern,key in [("raw","plan-*.json.gz","raw"),("raw","plan-*.json","raw"),("word-originals","plan-*.docx","word")]:
                    for file in (official/folder).glob(pattern):
                        match=re.search(r"plan-(\d+)",file.name)
                        if match:prior[int(match[1])].setdefault(key,file)
                for original in list((base/str(year)/"originals").glob("plan-*.docx"))+list((base/"originals"/str(year)).glob("plan-*.docx")):
                    match=re.search(r"plan-(\d+)",original.name)
                    if match:prior[int(match[1])].setdefault("word",original)
    return prior

def archive_ingestion_note():
    write_json(DIRECTORY/"archive-method.json", {
        "directory_source": BASE+"/page-center/major-program-search-view",
        "directory_method": "GET public search once per page, by grade; validate distinct IDs and totalRows.",
        "detail_method": "Request /major-program-search/info/{id}?skipAuth=1 or reuse a previously archived public response after grade, department, title and ID checks.",
        "detail_representation": "Compact UTF-8 JSON preserving response values, gzip compressed. The archive SHA-256 covers compressed bytes.",
        "word_method": "POST /major-program-search/export-word with form ids={id}, or reuse previously downloaded bytes. Validate ZIP CRC and the matching programme title in word/document.xml.",
        "dates": "date_snapshot denotes the local collection date. Reused originals may have been exported earlier. The publication or effective date is a separate field of each official plan.",
        "identity": "Use each directory row's DEPART_IDS and DEPART_NAME; keep minor, honours, international and integrated variants under their own programme IDs.",
        "absence": "A missing year in this public directory means zero matching directory rows at collection time.",
    })

def collect(row, cache):
    year=int(row["YEARS"])
    dept=row["DEPART_NAME"]
    pid=int(row["ID"])
    name=row["NAME_ZH"]
    root=DATA/dept/str(year)
    detail_url=f"{BASE}/major-program-search/info/{pid}?skipAuth=1"
    raw_file=root/"raw"/f"plan-{pid}.json.gz"
    word_file=root/"originals"/f"plan-{pid}.docx"
    raw_origin="public_api"
    if raw_file.exists():raw=gzip.decompress(raw_file.read_bytes())
    elif "raw" in cache:
        prior=cache["raw"]
        raw=gzip.decompress(prior.read_bytes()) if prior.suffix==".gz" else prior.read_bytes()
        raw_origin="previously_archived_public_api"
    else:raw=get(detail_url)
    detail=json.loads(raw)
    model=detail["model"]
    if int(model["id"])!=pid or int(model["grade"])!=year or int(model["department"]["id"])!=int(row["DEPART_IDS"]) or normalized(model["nameZh"])!=normalized(name):
        raise ValueError(f"Directory/detail mismatch {pid}")
    # Compact normalized JSON is lossless as a JSON value; the original Word bytes are preserved.
    if not raw_file.exists():
        compact=json.dumps(detail,ensure_ascii=False,separators=(",",":")).encode()
        put(raw_file,gzip.compress(compact,compresslevel=4,mtime=0))
    if word_file.exists():word=word_file.read_bytes()
    elif "word" in cache:word=cache["word"].read_bytes()
    else:word=get(f"{BASE}/major-program-search/export-word",{"ids":pid})
    with zipfile.ZipFile(io.BytesIO(word)) as document:
        if document.testzip():raise ValueError(f"Bad DOCX CRC {pid}")
        xml=ET.fromstring(document.read("word/document.xml"))
        text=normalized("".join(t.text or "" for t in xml.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")))
        if normalized(name) not in text[:2500]:
            raise ValueError(f"Word title mismatch {pid} / {text[:120]}")
    if not word_file.exists():put(word_file,word)
    return {"id":pid,"title":name,"year":year,"department":dept,"department_id":row["DEPART_IDS"],"major":row.get("MAJOR_NAME"),"detail_url":detail_url,"word_export_url":f"{BASE}/major-program-search/export-word","word_export_form":{"ids":pid},"raw_file":raw_file.relative_to(root).as_posix(),"word_file":word_file.relative_to(root).as_posix(),"raw_archive_sha256":sha(raw_file.read_bytes()),"word_sha256":sha(word),"word_bytes":len(word),"group_row_id":row.get("ROW_ID"),"date_snapshot":TODAY}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=8)
    parser.add_argument("--reuse-directory",action="store_true")
    args=parser.parse_args()
    rows=[]
    if args.reuse_directory and (DIRECTORY/"coverage.json").exists():
        for year in YEARS:
            for f in sorted(DIRECTORY.glob(f"directory-{year}-p*.json.gz")):rows.extend(json.loads(gzip.decompress(f.read_bytes()))["data"])
    else:
        with futures.ThreadPoolExecutor(max_workers=3) as pool:
            fetched=dict(zip(YEARS,pool.map(directory,YEARS)))
        calls=[]
        for year,(r,c) in fetched.items():rows.extend(r);calls.extend(c)
        write_json(DIRECTORY/"coverage.json",{"retrieved":TODAY,"calls":calls})
    cache=cached_sources()
    archive_ingestion_note()
    groups=collections.defaultdict(list)
    for row in rows:groups[row["DEPART_NAME"],int(row["YEARS"])].append(row)
    mapping=collections.defaultdict(dict)
    for (name,year),r in groups.items():mapping[name][year]=[int(p["ID"]) for p in r]
    write_json(DIRECTORY/"programme-ids.json",mapping)
    print("rows",len(rows),"groups",len(groups),"department_names",len(mapping),"local_cache_ids",len(cache),flush=True)
    # Make complete groups available progressively. Keep larger tasks running early.
    order=sorted(groups,key=lambda k:(not all(int(r["ID"]) in cache and len(cache[int(r["ID"])])==2 for r in groups[k]),k[0],k[1]))
    reports=collections.defaultdict(list)
    failed=[]
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        todo={pool.submit(collect,r,cache.get(int(r["ID"]),{})):(k,r) for k in order for r in groups[k]}
        for n,f in enumerate(futures.as_completed(todo),1):
            key,r=todo[f]
            try:reports[key].append(f.result())
            except Exception as exc:
                failed.append({"department":key[0],"year":key[1],"id":r["ID"],"error":str(exc)})
                print("ERROR",key,r["ID"],str(exc)[:220],flush=True)
            if len(reports[key])==len(groups[key]):
                write_json(DATA/key[0]/str(key[1])/"programmes.json",sorted(reports[key],key=lambda r:r["id"]))
                print("READY",key,len(reports[key]),flush=True)
            if n%10==0 or n==len(rows):
                write_json(ROOT/"fetch-status.json",{"total":len(rows),"processed":n,"ready":sum(len(reports[k])==len(v) for k,v in groups.items()),"failures":failed})
                print("PROGRESS",n,"/",len(rows),"failed",len(failed),flush=True)
    if failed:raise SystemExit(1)

if __name__=="__main__":main()
