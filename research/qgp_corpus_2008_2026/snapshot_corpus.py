#!/usr/bin/env python3
"""Create and verify a bounded same-machine /var/tmp snapshot of QGP research.
A different filesystem partition is NOT an off-device or cloud backup.
"""
import argparse, datetime, hashlib, io, json, os, pathlib, shutil, sqlite3, tarfile, tempfile

def sha(raw): return hashlib.sha256(raw).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--source",required=True)
 ap.add_argument("--backup-root",default="/var/tmp/worldshepherd-qgp-snapshots")
 ap.add_argument("--min-root-free-gb",type=float,default=3)
 a=ap.parse_args()
 src=pathlib.Path(a.source).expanduser().resolve()
 backup=pathlib.Path(a.backup_root).resolve()
 if src==backup or backup.is_relative_to(src) or src.is_relative_to(backup):
  raise SystemExit("Unsafe nested source/target")
 if shutil.disk_usage(str(backup.parent)).free < a.min_root_free_gb*1024**3:
  raise SystemExit("Low backup partition space")
 backup.mkdir(parents=True,exist_ok=True,mode=0o700)
 os.chmod(backup,0o700)
 now=datetime.datetime.now(datetime.timezone.utc)
 label=now.strftime("%Y%m%dT%H%M%SZ")
 target=backup/("qgp_corpus_"+label+".tar.gz")
 dbsrc=src/"metadata/qgp.sqlite3"
 tmpdir=pathlib.Path(tempfile.mkdtemp(prefix=".qgp-snapshot-",dir=str(backup)))
 try:
  clean=tmpdir/"qgp.sqlite3"
  with sqlite3.connect("file:"+str(dbsrc)+"?mode=ro",uri=True) as c:
   with sqlite3.connect(str(clean)) as out: c.backup(out)
  with sqlite3.connect(str(clean)) as c:
   integrity=c.execute("PRAGMA integrity_check").fetchone()[0]
   works=c.execute("SELECT count(*) FROM works").fetchone()[0]
   observations=c.execute("SELECT count(*) FROM observations").fetchone()[0]
  if integrity!="ok": raise RuntimeError("SQLite integrity failed")
  stage=json.loads((src/"sara_staging/export_manifest.json").read_text())
  if stage["total_records"]!=works:raise RuntimeError("Staging count != indexed works")
  screeningdb=src/"screening/screening.sqlite3"
  if screeningdb.exists():
   with sqlite3.connect("file:"+str(screeningdb)+"?mode=ro",uri=True) as sc:
    screen_count=sc.execute("SELECT count(*) FROM screening").fetchone()[0]
   if screen_count!=works:raise RuntimeError("Screening count != indexed works")
  files=[("metadata/qgp.sqlite3",clean)]
  for r in [
   "metadata/critical_references.json","metadata/last_run.json",
   "hepdata/147195/manifest.json","hepdata/147195/record.json",
   "hepdata/147195/table_01.json","hepdata/147195/table_02.json",
   "hepdata/147195/table_03.json","hepdata/147195/table_04.json",
   "hepdata/147195/table_05.json",
   "sara_staging/ws_physics_external_sources.jsonl",
   "sara_staging/export_manifest.json","sara_staging/hepdata_review_record.json",
   "screening/screening.sqlite3","screening/screening_summary.json",
   "audits/date_audit.jsonl","audits/date_audit_summary.json",
   "thermometry_validation.json",
   "harvest_qgp.py","export_ws_physics.py","screen_relevance.py",
   "audit_dates.py","pin_critical_references.py","validate_thermometry.py",
   "snapshot_corpus.py"
  ]:
   p=src/r
   if p.exists():files.append((r,p))
  # STAR 2026 HEPData: guard all 26 public CC0 tables and include them in backup.
  extroot=src/"external_models/star_baryon_2026"
  hd=extroot/"hepdata_154708"
  hmanifest=hd/"manifest.json"
  if not hmanifest.exists():raise RuntimeError("STAR 2026 manifest missing")
  h=json.loads(hmanifest.read_text())
  if h["table_count"]!=26 or h.get("errors"):raise RuntimeError("STAR HEPData incomplete")
  for row in h["tables"]:
   rel="external_models/star_baryon_2026/hepdata_154708/table_%02d.json"%row["id"]
   p=src/rel
   if not p.is_file() or sha(p.read_bytes())!=row["sha256"]:
    raise RuntimeError("STAR 2026 source hash mismatch: "+rel)
   files.append((rel,p))
  for rel in [
   "external_models/star_baryon_2026/hepdata_154708/manifest.json",
   "external_models/star_baryon_2026/hepdata_154708_metadata.json",
   "external_models/star_baryon_2026/Baryon_Junction_Theoretical_curves.tar.gz",
   "external_models/star_baryon_2026/README",
   "external_models/star_baryon_2026/model_comparison_2026.json",
   "external_models/star_baryon_2026/rapidity_slope_consistency.json",
   "external_models/star_baryon_2026/star_2025_imr_fit.json",
   "fetch_star_baryon_2026.py","analyze_baryon_transport_2026.py",
   "fit_photonuclear_slope_2026.py","fit_star_imr_2025.py","test_science_baselines.py"
  ]:
   p=src/rel
   if not p.is_file():raise RuntimeError("STAR published-source payload missing: "+rel)
   files.append((rel,p))
  checks={name:{"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for name,p in files}
  manifest={"created_utc":now.isoformat(),"snapshot_type":"same_machine_other_partition_not_cloud",
            "source_path":str(src),"record_counts":{"works":works,"observations":observations},
            "sqlite_integrity":integrity,"source_files":checks,"file_count":len(files),"private_prereg_excluded":True,
            "staging_records":stage["total_records"],"staging_sha256":stage["jsonl_sha256"]}
  payload=(json.dumps(manifest,indent=2)+"\n").encode()
  with tarfile.open(str(target),"w:gz") as tar:
   for name,p in files:tar.add(str(p),arcname=name,recursive=False)
   info=tarfile.TarInfo("SNAPSHOT_MANIFEST.json")
   info.size=len(payload)
   info.mtime=int(now.timestamp())
   tar.addfile(info,io.BytesIO(payload))
  os.chmod(target,0o600)
  with tarfile.open(str(target),"r:gz") as tar:
   for name, meta in checks.items():
    member=tar.extractfile(name)
    if member is None or sha(member.read())!=meta["sha256"]:
     raise RuntimeError("Archive digest mismatch: "+name)
   found=json.loads(tar.extractfile("SNAPSHOT_MANIFEST.json").read())
   if found["record_counts"]["works"]!=works:raise RuntimeError("Archive index mismatch")
  sidecar=target.with_suffix(".manifest.json")
  sidecar.write_text(json.dumps({"archive":str(target),"archive_sha256":sha(target.read_bytes()),
                                 "archive_bytes":target.stat().st_size,**manifest},indent=2)+"\n")
  os.chmod(sidecar,0o600)
  print(json.dumps({"status":"VERIFIED_LOCAL_SECOND_PARTITION","archive":str(target),
                    "works":works,"observations":observations,"file_count":len(files),
                    "archive_bytes":target.stat().st_size,"archive_sha256":sha(target.read_bytes())}))
 finally:
  shutil.rmtree(str(tmpdir))
if __name__=="__main__": main()
