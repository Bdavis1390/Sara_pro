#!/usr/bin/env python3
"""Read NIST MDS2-2628 ZIP index and selected JSON using HTTP Range.
Does not download the full ~0.8-1.0 GB archives. Read-only metadata.
"""
import argparse,collections,datetime,hashlib,io,json,pathlib,re,urllib.request,zipfile
from urllib.parse import urlparse,quote
BASE="https://data.nist.gov/od/ds/ark:/88434/mds2-2628/"
FILES={"sdr0":"imd3%20sdr0.zip","sdr1":"imd3%20sdr1.zip"}
class HTTPRange(io.RawIOBase):
 def __init__(self,url,block=1048576):
  self.url=url;self.pos=0;self.block=block;self.cache=collections.OrderedDict()
  self.requests=0;self.bytes_downloaded=0
  u=urlparse(url)
  if u.scheme!="https" or u.hostname!="data.nist.gov":raise ValueError("Not a NIST source")
  r=urllib.request.Request(url,method="HEAD",headers={"User-Agent":"WorldShepherd-NIST-RF-MetadataAudit/1.0"})
  with urllib.request.urlopen(r,timeout=20) as conn:
   self.size=int(conn.headers["Content-Length"])
  if self.size>1_100_000_000:raise ValueError("Zip unexpectedly large")
 def seekable(self):return True
 def readable(self):return True
 def seek(self,offset,whence=0):
  pos=offset if whence==0 else (self.pos+offset if whence==1 else self.size+offset)
  if pos<0:raise ValueError("Negative offset")
  self.pos=pos
  return pos
 def tell(self):return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  n=min(n,max(0,self.size-self.pos))
  chunks=[]
  while n:
   bi=self.pos//self.block
   start=bi*self.block
   if bi not in self.cache:
    end=min(self.size,start+self.block)-1
    req=urllib.request.Request(self.url,headers={"Range":f"bytes={start}-{end}","User-Agent":"WorldShepherd-NIST-RF-MetadataAudit/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:
     if r.status!=206 or not r.headers.get("Content-Range","").startswith(f"bytes {start}-"):
      raise RuntimeError("Server ignored byte-range")
     data=r.read(self.block+1)
    if len(data)!=end-start+1:raise RuntimeError("Short byte-range")
    self.cache[bi]=data;self.requests+=1;self.bytes_downloaded+=len(data)
    while len(self.cache)>16:self.cache.popitem(last=False)
   self.cache.move_to_end(bi)
   p=self.pos-start
   out=self.cache[bi][p:p+n]
   chunks.append(out);self.pos+=len(out);n-=len(out)
  return b"".join(chunks)

def inspect(which,outpath):
 h=HTTPRange(BASE+FILES[which])
 with zipfile.ZipFile(h) as z:
  info=z.infolist()
  if len(info)>25000:raise RuntimeError("Unexpected zip entries")
  listmeta=[]
  for x in info:
   if x.file_size>150_000_000:raise RuntimeError("Unusually huge per-entry file")
   if ".." in pathlib.PurePosixPath(x.filename).parts:raise RuntimeError("Zip traversal entry")
   listmeta.append({"name":x.filename,"uncompressed_bytes":x.file_size,"compressed_bytes":x.compress_size,"crc32_hex":f"{x.CRC:08x}"})
  jsons={}
  for x in info:
   if x.filename.endswith(".json") and x.file_size<=2_000_000:
    body=z.read(x)
    try: v=json.loads(body)
    except json.JSONDecodeError:continue
    jsons[x.filename]={"sha256":hashlib.sha256(body).hexdigest(),"content":v}
  report={"as_of_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "NIST_dataset":"https://doi.org/10.18434/mds2-2628",
    "nist_2022_source":"https://data.nist.gov/od/id/mds2-2628",
    "archive":FILES[which],"zip_total_bytes":h.size,"entries":len(info),
    "uncompressed_bytes":sum(x.file_size for x in info),
    "compressed_bytes_of_entries":sum(x.compress_size for x in info),
    "index":listmeta,"json_metadata":jsons,
    "range_requests":h.requests,"downloaded_bytes":h.bytes_downloaded,
    "rights":"NIST public data, NIST Open Access license",
    "physics_claim":"NONE",
    "sources":"PUBLIC_INDEPENDENT_NIST_MEASUREMENT_DATA_NOT_WORLDSHEPHERD_DATA"}
 out=pathlib.Path(outpath);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({"which":which,"entry_count":len(info),
    "stored_zip_bytes":h.size,"uncompressed_total_bytes":report["uncompressed_bytes"],
    "metadata_names":list(jsons),
    "example_members":listmeta[:8],"downloaded_bytes":h.bytes_downloaded,
    "http_range_requests":h.requests}))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--which",choices=list(FILES),default="sdr0")
 p.add_argument("--out",required=True)
 a=p.parse_args()
 inspect(a.which,a.out)
