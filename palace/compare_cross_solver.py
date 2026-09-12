#!/usr/bin/env python3
"""Post-convergence numerical cross-solver comparison.

Computes descriptive complex-S11 disagreement only. It intentionally defines no
physics-validation pass threshold. A second numerical solver cannot substitute
for calibrated VNA measurement or independent physical replication.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,tempfile
from pathlib import Path


def digest(p):
    h=hashlib.sha256();
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def read(p):
    d={}
    with p.open(newline='',encoding='utf-8') as f:
        r=csv.DictReader(f)
        if not {'frequency_ghz','real','imag'}.issubset(r.fieldnames or []): raise ValueError('canonical complex-S11 columns required')
        for x in r:
            k=round(float(x['frequency_ghz']),12); z=complex(float(x['real']),float(x['imag']))
            if k in d: raise ValueError('duplicate frequency')
            if not all(math.isfinite(v) for v in (k,z.real,z.imag)): raise ValueError('non-finite sample')
            d[k]=z
    if len(d)<2: raise ValueError('insufficient samples')
    return d


def wrap(x): return (x+180)%360-180

def phase(z): return math.degrees(math.atan2(z.imag,z.real))

def compare(a,b,min_common=101):
    x,y=read(a),read(b); common=sorted(set(x)&set(y))
    if len(common)<min_common: raise ValueError(f'need at least {min_common} exact common frequency points')
    dif=[abs(x[f]-y[f]) for f in common]
    rms=math.sqrt(sum(v*v for v in dif)/len(dif))
    norm=rms/max(math.sqrt(sum(abs(y[f])**2 for f in common)/len(common)),1e-15)
    phase_rms=math.sqrt(sum(wrap(phase(x[f])-phase(y[f]))**2 for f in common)/len(common))
    return {'schema':'WS-PALACE-CROSS-SOLVER-REPORT-V1','common_frequency_points':len(common),'metrics':{'max_abs_delta_complex_s11':max(dif),'rms_abs_delta_complex_s11':rms,'complex_normalized_rmse':norm,'phase_rmse_deg':phase_rms},'digests':{'palace_sha256':digest(a),'comparator_sha256':digest(b)},'evidence_class':'INTERNAL_NUMERICAL_CROSSCHECK_ONLY','physics_validation_gate':'NOT_DEFINED','external_gate_effect':'NONE','claims_boundary':'Agreement or disagreement between numerical solvers is diagnostic numerical evidence only. It is not calibrated measurement, partner validation, independent physical replication, qualification, or certification.'}


def write(p,offset=0):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['frequency_ghz','real','imag']);w.writeheader()
        for i in range(121):
            q=8+4*i/120; z=complex(.2+.3*abs(q-10)/2+offset,.01)
            w.writerow({'frequency_ghz':f'{q:.12f}','real':z.real,'imag':z.imag})

def selftest():
    with tempfile.TemporaryDirectory() as td:
        d=Path(td);a=d/'a.csv';b=d/'b.csv';write(a);write(b,.001);r=compare(a,b);assert r['common_frequency_points']==121 and r['external_gate_effect']=='NONE' and r['physics_validation_gate']=='NOT_DEFINED'
        try: compare(a,b,122)
        except ValueError: pass
        else: raise AssertionError('minimum-common fail-closed test failed')
    print('PALACE cross-solver comparator self-test: PASS')

def main():
    p=argparse.ArgumentParser();p.add_argument('--palace',type=Path);p.add_argument('--comparator',type=Path);p.add_argument('--output',type=Path);p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:selftest();return
    if not all((a.palace,a.comparator,a.output)):p.error('--palace --comparator --output required')
    r=compare(a.palace,a.comparator);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['metrics'],indent=2))
if __name__=='__main__':main()
