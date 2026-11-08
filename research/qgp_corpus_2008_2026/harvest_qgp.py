#!/usr/bin/env python3
"""WorldShepherd QGP 2008-2026: resumable metadata-only INSPIRE/OpenAlex harvester."""
import argparse, datetime, hashlib, json, pathlib, shutil, sqlite3, time
import urllib.parse, urllib.request, urllib.error, zlib

TOPICS = [
 "quark gluon plasma", "lattice QCD", "QCD phase diagram",
 "heavy ion collisions", "dilepton thermal", "direct photons heavy ion",
 "jet quenching", "heavy quark transport", "quarkonia suppression",
 "flow coefficients heavy ion", "chiral magnetic effect", "magnetic field heavy ion",
 "electromagnetic conductivity QGP", "baryon number transport", "baryon junction",
 "critical point fluctuations", "strangeness enhancement", "oxygen oxygen collisions",
 "sPHENIX", "shear viscosity QCD", "hyperon spin polarization",
 "non Gaussian heavy quark"
]
STAMP = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
HASH = lambda b: hashlib.sha256(b).hexdigest()
AGENT = "WorldShepherd-QGP-Corpus/2.0 (scientific metadata, low-rate, no bulk text)"

def connect(out):
    c = sqlite3.connect(str(out / "qgp.sqlite3"))
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS works(
      id TEXT PRIMARY KEY,title TEXT,year INTEGER,doi TEXT,first_seen TEXT,last_seen TEXT);
    CREATE TABLE IF NOT EXISTS observations(
      provider TEXT,provider_id TEXT,topic TEXT,work_id TEXT,url TEXT,
      fetched_at TEXT,sha256 TEXT,metadata_zlib BLOB,
      PRIMARY KEY(provider,provider_id,topic));
    CREATE TABLE IF NOT EXISTS pages(
      provider TEXT,topic TEXT,year INTEGER,page INTEGER,items INTEGER,
      terminal INTEGER,fetched_at TEXT,url TEXT,sha256 TEXT,
      PRIMARY KEY(provider,topic,year,page));
    CREATE TABLE IF NOT EXISTS errors(provider TEXT,topic TEXT,year INTEGER,
      page INTEGER,error TEXT,observed_at TEXT);
    CREATE INDEX IF NOT EXISTS works_year ON works(year);
    """)
    c.commit()
    return c

def get(url):
    req = urllib.request.Request(url,headers={"User-Agent":AGENT,"Accept":"application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                raw = r.read(6000001)
                if len(raw)>6000000: raise ValueError("Too large for metadata request")
                return raw
        except urllib.error.HTTPError as e:
            if e.code==429: raise  # Never retry API-budget/rate-limit exhaustion in this invocation
            if e.code not in (500,502,503,504) or attempt==2: raise
            time.sleep(5*(attempt+1))
        except (TimeoutError,urllib.error.URLError):
            if attempt==2: raise
            time.sleep(5*(attempt+1))

def url_for(provider,topic,year,page,size):
    if provider == "inspire":
        params={"q":'"'+topic+'" and de '+str(year),"size":size,"page":page,
                "sort":"mostrecent","fields":"titles,dois,arxiv_eprints,earliest_date,publication_info,keywords,document_type,control_number,citation_count"}
        return "https://inspirehep.net/api/literature?"+urllib.parse.urlencode(params)
    params={"search":topic,"filter":"publication_year:"+str(year),
            "per_page":size,"page":page,
            "select":"id,doi,display_name,publication_year,publication_date,cited_by_count,type,open_access,primary_location,topics"}
    return "https://api.openalex.org/works?"+urllib.parse.urlencode(params)

def entries(provider,body):
    obj=json.loads(body)
    if provider=="inspire": return obj["hits"]["hits"], obj["hits"].get("total")
    return obj["results"],obj["meta"].get("count")

def add(c,provider,topic,record,cutoff):
    if provider=="inspire":
        m=record.get("metadata",{})
        rid=str(record.get("id",""))
        title=(m.get("titles") or [{}])[0].get("title","")
        doi=(m.get("dois") or [{}])[0].get("value","")
        arxiv=(m.get("arxiv_eprints") or [{}])[0].get("value","")
        day=m.get("earliest_date","")
        link="https://inspirehep.net/literature/"+rid
        data={k:m.get(k) for k in ("titles","dois","arxiv_eprints","earliest_date","publication_info","citation_count","document_type","control_number")}
    else:
        rid=str(record.get("id","")).split("/")[-1]
        title=record.get("display_name","")
        doi=record.get("doi") or ""
        arxiv=""
        day=record.get("publication_date","")
        link=record.get("id","")
        data={k:record.get(k) for k in ("id","doi","display_name","publication_year","publication_date","cited_by_count","type","open_access","primary_location","topics")}
    if not rid or (day and day[:10]>cutoff): return False
    doi=doi.lower().replace("https://doi.org/","").replace("http://doi.org/","").replace("doi:","").strip()
    key="doi:"+doi if doi else ("arxiv:"+arxiv if arxiv else provider+":"+rid)
    year=int(day[:4]) if day and day[:4].isdigit() else None
    ts=STAMP()
    payload=json.dumps(data,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()
    c.execute("INSERT INTO works VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen",(key,title,year,doi,ts,ts))
    c.execute("INSERT OR REPLACE INTO observations VALUES(?,?,?,?,?,?,?,?)",(provider,rid,topic,key,link,ts,HASH(payload),sqlite3.Binary(zlib.compress(payload,6))))
    return True

def resource_check(out,min_free_gb,max_db_mb):
    if shutil.disk_usage(str(out)).free<min_free_gb*1024**3:
        raise RuntimeError("Disk space safety guard")
    footprint=sum(p.stat().st_size for p in out.glob("qgp.sqlite3*"))
    if footprint>max_db_mb*1024**2:
        raise RuntimeError("Database size safety guard")

def run():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",default="./qgp_corpus")
    ap.add_argument("--years",default="2008-2026")
    ap.add_argument("--cutoff",default="2026-11-08")
    ap.add_argument("--providers",default="inspire,openalex")
    ap.add_argument("--per-page",type=int,default=40)
    ap.add_argument("--max-requests",type=int,default=12)
    ap.add_argument("--max-pages-per-query",type=int,default=1)
    ap.add_argument("--max-seconds",type=int,default=120)
    ap.add_argument("--min-free-gb",type=float,default=3)
    ap.add_argument("--max-db-mb",type=int,default=128)
    ap.add_argument("--delay",type=float,default=1.3)
    ap.add_argument("--topics",default="",help="Pipe-separated exact topics for priority harvesting")
    ap.add_argument("--refresh",action="store_true")
    ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args()
    date=datetime.date.fromisoformat(a.cutoff)
    if "-" in a.years: 
        first,last=[int(x) for x in a.years.split("-")]
        years=list(range(first,last+1))
    else: years=[int(x) for x in a.years.split(",")]
    providers=[s.strip() for s in a.providers.split(",")]
    selected=[s.strip() for s in a.topics.split("|") if s.strip()]
    topics=[t for t in TOPICS if not selected or t in selected]
    if selected and len(topics)!=len(set(selected)): ap.error("Unknown --topics value")
    if not years or min(years)<2008 or max(years)>date.year or any(p not in ("inspire","openalex") for p in providers):
        ap.error("Invalid year or source")
    if not 1<=a.per_page<=100 or a.delay<1 or a.max_requests<0:
        ap.error("Invalid limits")
    if a.dry_run:
        print("DRY RUN:",len(topics)*len(years)*len(providers),"query partitions")
        print(url_for(providers[0],TOPICS[0],years[0],1,a.per_page))
        return
    out=pathlib.Path(a.out).expanduser()
    out.mkdir(parents=True,exist_ok=True)
    resource_check(out,a.min_free_gb,a.max_db_mb)
    # Historical database was created with per_page=40. Persist a fixed page-size
    # invariant: changing it in place would shift page boundaries and silently omit data.
    config=out/"collection_config.json"
    if config.exists():
        previous=json.loads(config.read_text())
        if previous["per_page"]!=a.per_page: ap.error("Existing DB has a different per-page size; use a new --out")
    elif (out/"qgp.sqlite3").exists():
        if a.per_page!=40: ap.error("Legacy DB uses per_page=40; use a new --out for other sizes")
        config.write_text(json.dumps({"per_page":40,"version":2})+"\\n")
    else:
        config.write_text(json.dumps({"per_page":a.per_page,"version":2})+"\\n")
    c=connect(out)
    blocked_providers=set()
    start=time.monotonic()
    nreq=added=fail=0
    def budget():
        return nreq>=a.max_requests or time.monotonic()-start>=a.max_seconds
    for topic in topics:
        for year in years:
            for provider in providers:
                if provider in blocked_providers: continue
                page=1
                while not budget() and (not a.max_pages_per_query or page<=a.max_pages_per_query):
                    old=c.execute("SELECT terminal FROM pages WHERE provider=? AND topic=? AND year=? AND page=?",(provider,topic,year,page)).fetchone()
                    if old and not a.refresh:
                        if old[0]: break
                        page+=1
                        continue
                    resource_check(out,a.min_free_gb,a.max_db_mb)
                    url=url_for(provider,topic,year,page,a.per_page)
                    nreq+=1
                    try:
                        raw=get(url)
                        items,total=entries(provider,raw)
                        terminal=int(len(items)<a.per_page or (isinstance(total,int) and page*a.per_page>=total))
                        with c:
                            for item in items: added+=int(add(c,provider,topic,item,a.cutoff))
                            c.execute("INSERT OR REPLACE INTO pages VALUES(?,?,?,?,?,?,?,?,?)",(provider,topic,year,page,len(items),terminal,STAMP(),url,HASH(raw)))
                        print("OK",provider,year,topic,"page",page,"hits",len(items),flush=True)
                        if terminal: break
                        page+=1
                        time.sleep(a.delay)
                    except Exception as exc:
                        if isinstance(exc,urllib.error.HTTPError) and exc.code==429:
                            blocked_providers.add(provider)
                            print("RATE_LIMIT_CIRCUIT_OPEN",provider,"no further requests to provider during this run",flush=True)
                        fail+=1
                        with c:
                            c.execute("INSERT INTO errors VALUES(?,?,?,?,?,?)",(provider,topic,year,page,str(exc)[:500],STAMP()))
                        print("ERROR",provider,year,str(exc)[:120],flush=True)
                        break
                if budget(): break
            if budget(): break
        if budget(): break
    report={"requests":nreq,"record_observations":added,"errors":fail,
            "unique_works":c.execute("SELECT COUNT(*) FROM works").fetchone()[0],
            "provenance_rows":c.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
            "pages":c.execute("SELECT COUNT(*) FROM pages").fetchone()[0],
            "rate_limited_providers":sorted(blocked_providers),
            "utc":STAMP(),"cutoff":a.cutoff,"metadata_only":True}
    (out/"last_run.json").write_text(json.dumps(report,indent=2)+"\n")
    print("SUMMARY",json.dumps(report),flush=True)
    c.close()

if __name__=="__main__": run()
