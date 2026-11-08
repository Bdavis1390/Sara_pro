#!/usr/bin/env python3
"""Pin canonical historically important QGP papers independent of search rank."""
import argparse,json,pathlib,sqlite3,urllib.parse
from harvest_qgp import connect,get,add,resource_check
DOIS=[
 "10.1103/PhysRevD.78.074033",
 "10.1016/j.physletb.2019.05.013",
 "10.1103/PhysRevX.14.011028",
 "10.1038/s41467-025-63216-5",
 "10.1126/science.ads5962",
 "10.1103/7fd5-1kq5",
 "10.1103/d4vl-88fl",
 "10.1038/s41586-025-09920-0",
 "10.1146/annurev-nucl-100324-014902"
]
def main():
 a=argparse.ArgumentParser()
 a.add_argument("--out",required=True)
 a.add_argument("--cutoff",default="2026-11-08")
 p=a.parse_args()
 out=pathlib.Path(p.out);out.mkdir(parents=True,exist_ok=True)
 resource_check(out,3,128)
 c=connect(out)
 success=[];errors=[]
 for doi in DOIS:
  url="https://api.openalex.org/works/https://doi.org/"+urllib.parse.quote(doi,safe="/")
  try:
   work=json.loads(get(url))
   actual=str(work.get("doi","")).lower().replace("https://doi.org/","")
   if actual!=doi.lower():raise ValueError("DOI mismatch")
   with c: add(c,"openalex","curated_mandatory",work,p.cutoff)
   success.append({"doi":doi,"id":work.get("id"),"title":work.get("display_name"),"year":work.get("publication_year")})
   print("PINNED",doi,flush=True)
  except Exception as exc:
   errors.append({"doi":doi,"reason":str(exc)})
   print("ERROR",doi,str(exc)[:120],flush=True)
 (out/"critical_references.json").write_text(json.dumps({"verified":success,"errors":errors},indent=2)+"\n")
 print("SUMMARY",json.dumps({"verified":len(success),"errors":len(errors),
      "total_works":c.execute("select count(*) from works").fetchone()[0]}))
 c.close()
if __name__=="__main__":main()
