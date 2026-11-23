#!/usr/bin/env python3
"""Acquire bounded third-party measured RF S2P files from a public Zenodo record.
Raw files STAY LOCAL because license metadata is unspecified; none are committed.
No hardware is operated. Original instrument calibration is asserted by publisher,
not independently verified by WorldShepherd.
"""
import argparse,datetime,hashlib,json,os,pathlib,re,shutil,urllib.request
from urllib.parse import urlparse

RECORD="20186567"
API=f"https://zenodo.org/api/records/{RECORD}"
KNOWN_TITLE="S-parameter measurements of Memristors between 70kHz and 160 GHz"
MAX_FILE_BYTES=200000
MIN_FREE_BYTES=2_000_000_000

def download(url,max_size):
 u=urlparse(url)
 if u.scheme!="https" or u.hostname!="zenodo.org":
  raise ValueError("Unexpected download host; network boundary blocked")
 req=urllib.request.Request(url,headers={"User-Agent":"WorldShepherd-MOSAIC-RF-PublicDataAudit/1.0"})
 with urllib.request.urlopen(req,timeout=24) as stream:
  data=stream.read(max_size+1)
 if len(data)>max_size:raise ValueError("File exceeds download budget")
 return data

def checksum(data):return hashlib.md5(data).hexdigest(),hashlib.sha256(data).hexdigest()
def ingest(root):
 root=pathlib.Path(root)
 root.mkdir(parents=True,exist_ok=True)
 if shutil.disk_usage(root).free<MIN_FREE_BYTES:raise RuntimeError("Local disk safety threshold failed")
 data=json.loads(download(API,700000))
 meta=data["metadata"]
 if meta["title"]!=KNOWN_TITLE:raise ValueError("Unexpected source dataset")
 fs=data.get("files",[])
 if len(fs)!=12:raise ValueError("File list incomplete/expanded unexpectedly; manual review")
 records=[]
 for file in sorted(fs,key=lambda f:f["key"]):
  name=file["key"]
  if not re.fullmatch(r"[A-Za-z0-9_.-]+\.S2P",name):
   raise ValueError("Unexpected source filename")
  if not 130000<=int(file["size"])<=MAX_FILE_BYTES:
   raise ValueError("Unexpected input file size")
  if not file["checksum"].startswith("md5:"):
   raise ValueError("No expected source checksum")
  expected=file["checksum"].split(":",1)[1]
  target=root/name
  if target.exists():
   raw=target.read_bytes()
  else:
   raw=download(file["links"]["self"],MAX_FILE_BYTES)
  md5,sha256=checksum(raw)
  if len(raw)!=int(file["size"]) or md5!=expected:
   raise ValueError("Downloaded S2P does not match publisher checksum: "+name)
  if not target.exists():
   temp=target.with_suffix(".partial")
   temp.write_bytes(raw)
   temp.replace(target)
   target.chmod(0o600)
  records.append({"filename":name,"size":len(raw),"source_md5":md5,
                  "local_sha256":sha256,"uri":file["links"]["self"]})
 report={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "source_title":KNOWN_TITLE,"source_url":f"https://zenodo.org/records/{RECORD}",
  "source_doi":f"10.5281/zenodo.{RECORD}",
  "provenance":"EXTERNAL_LAB_MEASURED_PUBLISHER_REPORTED_NOT_WORLDSHEPHERD_MEASURED",
  "laboratory":"CEA Leti / TERRAMETA project","laboratory_reported_instrument":"Anritsu ME7838G VectorStar VNA, LRRM calibrated",
  "lab_temperature_C":25,"declared_range_Hz":[70000,160000000000],
  "rights_metadata_present":meta.get("rights") is not None,
  "license_reuse_status":"UNVERIFIED_PRESERVE_RAW_FILES_LOCALLY_NO_REPUBLICATION",
  "raw_s2p_files":records,
  "verified_file_count":len(records),
  "verified_total_bytes":sum(x["size"] for x in records),
  "metadata_authentication":"Zenodo API and MD5 checksums; independent actual calibration certificates not supplied",
  "physical_discovery":False}
 outfile=root.parent/"terrameta_local_manifest.json"
 outfile.write_text(json.dumps(report,indent=2)+"\n")
 outfile.chmod(0o600)
 print(json.dumps({"source":report["source_doi"],"count":len(records),
 "bytes":report["verified_total_bytes"],"rights_unverified":not report["rights_metadata_present"],
 "manifest":str(outfile),"worldshepherd_experimental_measurements":False}))
 return report

if __name__=="__main__":
 ap=argparse.ArgumentParser()
 ap.add_argument("--destination",required=True)
 args=ap.parse_args()
 ingest(args.destination)
