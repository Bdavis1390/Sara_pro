#!/usr/bin/env python3
"""Audits original work-year vs journal/publication-year mismatches without overwriting sources."""
import argparse, collections, datetime, json, pathlib, sqlite3, zlib
def valid(x):
 try:
  y=int(x)
  return y if 1900<=y<=2030 else None
 except (ValueError,TypeError): return None
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--db",required=True)
 ap.add_argument("--out",required=True)
 a=ap.parse_args()
 out=pathlib.Path(a.out).expanduser();out.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect("file:"+str(pathlib.Path(a.db).resolve())+"?mode=ro",uri=True)
 seen={}; publication={}
 for k,year in c.execute("SELECT id,year FROM works"):
  seen[k]={"index_year":year,"earliest_years":[],"journal_years":[],"openalex_years":[],"published_dates":[]}
 for key,prov,raw in c.execute("SELECT work_id,provider,metadata_zlib FROM observations"):
  if key not in seen: continue
  obj=json.loads(zlib.decompress(raw))
  s=seen[key]
  if prov=="inspire":
   er=valid(str(obj.get("earliest_date") or "")[:4])
   if er:s["earliest_years"].append(er)
   for p in obj.get("publication_info") or []:
    jy=valid(p.get("year"))
    if jy:s["journal_years"].append(jy)
  if prov=="openalex":
   py=valid(obj.get("publication_year"))
   if py:s["openalex_years"].append(py)
   date=obj.get("publication_date")
   if date:s["published_dates"].append(date)
 counts=collections.Counter()
 rows=[]
 for key,fields in seen.items():
  # Publication year preferred over preprint year when provided by a publisher/aggregator.
  years=fields["openalex_years"] or fields["journal_years"] or fields["earliest_years"]
  pub=min(years) if years else fields["index_year"]
  earliest=min(fields["earliest_years"]) if fields["earliest_years"] else fields["index_year"]
  journal=min(fields["journal_years"]) if fields["journal_years"] else None
  discrepancy=pub is not None and fields["index_year"] is not None and pub!=fields["index_year"]
  if discrepancy:counts["year_differs"]+=1
  if journal and earliest and journal>earliest:counts["journal_after_preprint"]+=1
  if pub and pub>2026:counts["publication_after_2026"]+=1
  counts["records"]+=1
  row={"id":key,"index_year":fields["index_year"],"publication_year_best_effort":pub,
       "earliest_known_year":earliest,"journal_year":journal,
       "publication_dates":sorted(set(fields["published_dates"])),
       "index_publication_year_disagree":bool(discrepancy),
       "publication_year_basis":"openalex" if fields["openalex_years"] else ("inspire_journal" if journal else "inspire_earliest_or_index")}
  rows.append(row)
 with (out/"date_audit.jsonl").open("w") as f:
  for r in rows:f.write(json.dumps(r,sort_keys=True)+"\n")
 examples=[r for r in rows if r["index_publication_year_disagree"]][:25]
 summary={"count":dict(counts),"examples":examples,
     "note":"Best-effort publication year audit from provider metadata; historical earliest preprint dates are not publication dates. Competing metadata must be manually resolved.",
     "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat()}
 (out/"date_audit_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps({"record_count":counts["records"],"year_discrepancies":counts["year_differs"],"journal_after_preprint":counts["journal_after_preprint"],"future_pubs":counts["publication_after_2026"]}))
 if counts["records"]<1:raise SystemExit(2)
if __name__=="__main__":main()
