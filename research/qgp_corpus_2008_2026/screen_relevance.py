#!/usr/bin/env python3
"""Screen a QGP literature index into auditable title-evidence tiers.
Tiers are triage labels; they are NOT peer review or experimental validation.
Read-only source database, separate SQLite output and JSON summary.
"""
import argparse, collections, datetime, hashlib, json, pathlib, re, sqlite3

CORE = {
 "qgp":r"\bqgp\b|\bquark[\s\-–]*gluon[\s\-–]*plasma\b",
 "heavy_ion":r"heavy[\s\-–]*ion.*collis|relativistic heavy[\s\-–]*ion|\bpb[\s\-+]*pb\b|\bau[\s\-+]*au\b",
 "qcd_phase":r"\bqcd.{0,30}(?:phase|crossover|critical|equation of state|thermal|deconfin|thermodyn)",
 "thermal_probe":r"thermal.{0,30}(?:dilepton|photon|radiation)|(?:dilepton|dielectron).{0,35}(?:spectrum|thermal|heavy[\s\-–]*ion|quark)",
 "transport":r"jet quench|heavy[\s\-–]*quark.{0,30}(?:diffusion|transport|loss)|parton energy loss",
 "baryon":r"baryon.{0,30}(?:junction|transport|stopping)|baryon number.{0,25}(?:transfer|transport)",
 "em_response":r"chiral magnetic effect|charge[\s\-–]*dependent directed flow|electromagnetic conductivity",
 "detector":r"\b(?:sphenix|phenix|star|alice)\b.{0,45}(?:collis|quark|plasma|measurement|jet|flow)|\bRHIC\b",
 "lattice":r"\blattice[\s\-–]*qcd\b",
}
ADJACENT={
 "qcd":r"\bqcd\b|\bquantum chromodynamics\b",
 "quarks":r"\bquarks?\b|\bgluons?\b|\bpartons?\b",
 "hadron":r"\bhadron\w*|\bbaryon\w*|\bmeson\w*",
 "nuclear":r"\bnuclear\b|\brelativistic\b|\bplasma\b",
 "detector":r"\bcern\b|\blhc\b|\brhic\b|\bphenix\b|\bsphenix\b",
}
PROJECTS = {
 "Junction Discrimination":r"baryon.{0,30}(?:junction|number|transport|stopping)",
 "QGP thermometry":r"(?:thermal|temperature|thermometr|dilepton|dielectron|photon).{0,60}(?:quark|plasma|heavy|ion|qcd)|qgp.{0,35}temperature",
 "Plasma transport":r"heavy.{0,15}quark|jet.{0,20}(?:quench|energy loss)|diffusion|viscosity|transport",
 "Field response":r"chiral magnetic|conductivity|electromagnetic field|magnetic effect|directed flow",
 "Small-system tests":r"oxygen[\s\-–]*oxygen|\boo\b.{0,20}collis|\bp[\s\-+]*pb\b",
 "QCD theory":r"lattice qcd|qcd phase|crossover|deconfinement|thermodynamic",
}
def tag(text, dictionary):
 return sorted(name for name,pat in dictionary.items() if re.search(pat,text,re.I))
def evaluate(title):
 core=tag(title,CORE)
 adjacent=tag(title,ADJACENT)
 if core: tier="CORE_TITLE_SIGNAL"
 elif adjacent: tier="ADJACENT_TITLE_SIGNAL"
 else: tier="UNCLASSIFIED_MANUAL_REVIEW"
 return tier,core,adjacent,tag(title,PROJECTS)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--database",required=True)
 ap.add_argument("--output",required=True)
 a=ap.parse_args()
 root=pathlib.Path(a.output).expanduser()
 root.mkdir(parents=True,exist_ok=True)
 src=sqlite3.connect("file:"+str(pathlib.Path(a.database).resolve())+"?mode=ro",uri=True)
 dst=sqlite3.connect(str(root/"screening.sqlite3"))
 dst.executescript("""DROP TABLE IF EXISTS screening;
 CREATE TABLE screening (canonical_id TEXT PRIMARY KEY,title TEXT,record_year INTEGER,doi TEXT,tier TEXT,core_tags TEXT,adjacent_tags TEXT,project_tags TEXT,source_fingerprint TEXT);
 CREATE INDEX IF NOT EXISTS idx_screen_tier ON screening(tier);
 CREATE INDEX IF NOT EXISTS idx_screen_year ON screening(record_year);
 """)
 records=src.execute("SELECT id, title, year, doi FROM works ORDER BY id").fetchall()
 tiers=collections.Counter()
 years=collections.defaultdict(lambda:collections.Counter())
 projects=collections.Counter()
 for key,title,year,doi in records:
  tier,core,adjacent,projs=evaluate(title or "")
  tiers[tier]+=1
  years[str(year or "unknown")][tier]+=1
  projects.update(projs)
  digest=hashlib.sha256((key+"\n"+str(title)).encode()).hexdigest()
  dst.execute("INSERT INTO screening VALUES(?,?,?,?,?,?,?,?,?)",
        (key,title,year,doi,tier,json.dumps(core),json.dumps(adjacent),json.dumps(projs),digest))
 dst.commit()
 summary={"records_screened":len(records),"tiers":dict(tiers),
  "candidate_project_tag_counts":dict(projects),
  "by_year":{key:dict(val) for key,val in sorted(years.items())},
  "method":"Title matching only; no abstracts or PDFs assessed; selection is not a causal connection",
  "further_review":"Independently review titles, abstracts, methods, corrections, licences, and full texts before assigning claims",
  "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (root/"screening_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
 out=(root/"candidate_shortlist.tsv").open("w")
 out.write("tier\tyear\tproject_tags\tid\ttitle\n")
 for row in dst.execute("""SELECT tier,record_year,project_tags,canonical_id,title FROM screening WHERE tier='CORE_TITLE_SIGNAL' ORDER BY record_year DESC,canonical_id LIMIT 1000"""):
  out.write("\t".join(str(x).replace("\t"," ").replace("\n"," ") for x in row)+"\n")
 out.close()
 test_cases=[
 ("Quark-Gluon Plasma Formation in Heavy Ion Collisions","CORE_TITLE_SIGNAL"),
 ("Baryon Junctions in Heavy-Ion Collisions","CORE_TITLE_SIGNAL"),
 ("Bayesian Optimization of Oncology Treatment","UNCLASSIFIED_MANUAL_REVIEW"),
 ("An Architecture for Neural Data Compression","UNCLASSIFIED_MANUAL_REVIEW"),
 ("QCD Radiative Corrections","ADJACENT_TITLE_SIGNAL"),
 ]
 tests=[{"title":title,"expected":expected,"actual":evaluate(title)[0]} for title,expected in test_cases]
 summary["test_cases"]=tests
 (root/"screening_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps({"total":len(records),"tiers":dict(tiers),"tags":dict(projects),"tests_passed":sum(t["expected"]==t["actual"] for t in tests),"tests_total":len(tests)}))
 if any(t["expected"]!=t["actual"] for t in tests):raise SystemExit(2)
 src.close();dst.close()
if __name__=="__main__":main()
