#!/usr/bin/env python3
"""WorldShepherd RF evidence validator, data-only. Does not control RF hardware.
EXPERIMENTAL DATA REQUIRED; synthetic tests cannot establish a physical effect.
"""
import argparse,collections,csv,datetime,hashlib,itertools,json,math,pathlib,statistics

NEEDED={"experiment_id","pair_id","replicate_id","sample_type","condition",
        "output_frequency_hz","output_power_dbm","uncertainty_db",
        "instrument_id","calibration_id","timestamp_utc"}
CONDITIONS={"OFF","A","B","AB"}
SAMPLE_TYPES={"CANDIDATE","BLANK"}
MIX_FAMILIES={"WS-RF-001","WS-RF-002","WS-RF-003"}
DBM_TO_W=lambda dbm:1e-3*10**(dbm/10)
def exact_sign_flip_p(values):
    n=len(values)
    if n<3 or n>16:raise ValueError("exact sign flip supports 3..16 independent runs")
    obs=abs(sum(values))
    total=1<<n
    extreme=0
    for mask in range(total):
        s=sum((1 if mask&(1<<i) else -1)*v for i,v in enumerate(values))
        if abs(s)>=obs-1e-18:extreme+=1
    return extreme/total

def load(path):
    raw=path.read_bytes()
    if len(raw)>2_000_000:raise ValueError("max 2MB CSV; use separately bounded chunks")
    rdr=csv.DictReader(raw.decode("utf-8-sig").splitlines())
    if not NEEDED.issubset(set(rdr.fieldnames or [])):
        raise ValueError("required columns missing: "+str(sorted(NEEDED-set(rdr.fieldnames or []))))
    grouped=collections.defaultdict(dict)
    allrows=list(rdr)
    for r in allrows:
        key=(r["pair_id"],r["output_frequency_hz"],r["replicate_id"])
        typ=r["sample_type"]
        cond=r["condition"]
        if typ not in SAMPLE_TYPES or cond not in CONDITIONS:
            raise ValueError("unexpected sample_type/condition")
        for k in NEEDED:
            if not r[k].strip():raise ValueError("Missing "+k+" in "+str(key))
        if not r["calibration_id"].startswith("CAL-"):raise ValueError("Unverifiable calibration reference naming")
        if (typ,cond) in grouped[key]:raise ValueError("Duplicate condition in "+str(key))
        freq=float(r["output_frequency_hz"]); pow_dbm=float(r["output_power_dbm"])
        err=float(r["uncertainty_db"])
        if not 0<freq<=1e11 or not -200<=pow_dbm<=60 or not 0<err<=10:
            raise ValueError("Invalid frequency, power or uncertainty range")
        p=DBM_TO_W(pow_dbm)
        err_p=p*(math.log(10)/10)*err
        grouped[key][(typ,cond)]=(p,err_p,r["instrument_id"],r["calibration_id"])
    if not grouped:raise ValueError("Empty dataset")
    delta=collections.defaultdict(list)
    for key,conditions in grouped.items():
        required={(typ,c) for typ in SAMPLE_TYPES for c in CONDITIONS}
        if set(conditions)!=required:raise ValueError("Incomplete OFF/A/B/AB sample-blank conditions: "+str(key))
        # In one paired run, instruments/calibration identities must be documented and stable.
        ids={(v[2],v[3]) for v in conditions.values()}
        if len(ids)!=1:raise ValueError("Instrument/calibration changed within a paired replicate: "+str(key))
        def mix(typ):
            r=conditions
            d=r[(typ,"AB")][0]-r[(typ,"A")][0]-r[(typ,"B")][0]+r[(typ,"OFF")][0]
            err2=sum(r[(typ,c)][1]**2 for c in CONDITIONS)
            return d,err2
        da,ea=mix("CANDIDATE")
        db,eb=mix("BLANK")
        delta[(key[0],key[1])].append((key[2],da-db,ea+eb))
    return delta,hashlib.sha256(raw).hexdigest(),len(allrows)

def adjust_holm(raw):
    pairs=sorted(raw.items(),key=lambda item:item[1])
    m=len(pairs);adjusted={};prior=0.0
    for rank,(name,p) in enumerate(pairs):
        prior=max(prior,min(1.,p*(m-rank)))
        adjusted[name]=prior
    return adjusted

def analyze(path):
    delta,digest,nrows=load(path)
    summaries={};rawp={}
    for key,values in sorted(delta.items()):
        if len(values)<3:raise ValueError("Need at least 3 independent paired runs: "+str(key))
        if len(values)>16:raise ValueError("For exact p, split into <=16 independent runs")
        labels=[v[0] for v in values]
        if len(set(labels))!=len(labels):raise ValueError("Duplicate independent run ID")
        signals=[v[1] for v in values]
        p=exact_sign_flip_p(signals)
        measured_err=math.sqrt(sum(v[2] for v in values))/len(values)
        mean=statistics.mean(signals)
        repeat_se=statistics.stdev(signals)/math.sqrt(len(values))
        summaries[key]={"independent_runs":len(values),"paired_interaction_difference_W":mean,
                        "instrument_propagated_se_W":measured_err,
                        "repeatability_se_W":repeat_se,
                        "conservative_se_W":math.hypot(repeat_se,measured_err),
                        "exact_sign_flip_two_sided_p":p,
                        "possible_standard_nonlinear_mixing":True}
        rawp[key]=p
    adjusted=adjust_holm(rawp)
    rows=[]
    for (pair,freq),s in summaries.items():
        row={"pair_id":pair,"output_frequency_hz":float(freq),**s,
             "holm_adjusted_p_across_tested_outputs":adjusted[(pair,freq)],
             "claim_status":"NO_NEW_PHYSICS_INFERABLE_FROM_INTERACTION_ALONE"}
        rows.append(row)
    return {
      "date_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "experiment_sha256":digest,"data_rows":nrows,"results":rows,
      "is_synthetic":False,  # Caller must separately prove measurement authenticity.
      "fundamental_discovery_gate":"BLOCKED",
      "gate_reasons":["Calibration IDs are declarations and must be validated against traceable certificates",
       "No full complex S-parameters or independent absolute power closure supplied",
       "Known nonlinear mixing, interference and material response can generate this effect",
       "No independent second-laboratory replication and no prospectively specified new law",
       "The sign-flip test relies on independent exchangeable runs and symmetry under the null",
       "A positive result must survive sham frequencies, look-elsewhere, hardware and environmental artifact tests"],
      "measurement_status":"UNVERIFIED_SELF_REPORTED_CSV"}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    result=analyze(pathlib.Path(a.csv))
    path=pathlib.Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"rows":result["data_rows"],"results":len(result["results"]),
         "best_corrected_p":min(x["holm_adjusted_p_across_tested_outputs"] for x in result["results"]),
         "claim_status":result["fundamental_discovery_gate"]}))
if __name__=="__main__":main()
