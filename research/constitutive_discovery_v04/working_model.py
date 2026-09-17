"""Worldshepherd constitutive discovery v0.4 — synthetic-only research node."""
from dataclasses import dataclass
import math
import numpy as np

CLAIMS_STATE = "PROVEN INTERNALLY — SYNTHETIC ONLY"
EXECUTION_STATUS = "PROPOSED_NOT_EXECUTED"

@dataclass(frozen=True)
class DynamicSample:
    t: float
    strain: float
    stress: float

def generate(n=900, dt=.01, E_inf=500., E1=900., tau=.35, noise_std=.15, seed=9675):
    rng=np.random.default_rng(seed); z=0.; prev=0.; out=[]
    for i in range(n):
        t=i*dt
        eps=.025*math.sin(2*math.pi*.6*t)+.012*math.sin(2*math.pi*1.7*t)
        edot=(eps-prev)/dt if i else 0.
        z += dt*(E1*edot-z/tau)
        out.append(DynamicSample(t,eps,float(E_inf*eps+z+rng.normal(0,noise_std))))
        prev=eps
    return out

def fit_memoryless(samples):
    X=np.array([[s.strain] for s in samples]); y=np.array([s.stress for s in samples])
    c,*_=np.linalg.lstsq(X,y,rcond=None); p=X@c
    return {"E":float(c[0]),"rmse":float(np.sqrt(np.mean((y-p)**2)))}

def fit_one_state(samples,dt=.01,taus=None):
    if taus is None: taus=np.geomspace(.05,2.,80)
    y=np.array([s.stress for s in samples]); eps=np.array([s.strain for s in samples])
    edot=np.r_[0,np.diff(eps)/dt]; best=None
    for tau in taus:
        q=0.; qs=[]
        for e in edot:
            q += dt*(e-q/tau); qs.append(q)
        X=np.c_[eps,np.array(qs)]; c,*_=np.linalg.lstsq(X,y,rcond=None); p=X@c
        rmse=float(np.sqrt(np.mean((y-p)**2)))
        cand={"E_inf":float(c[0]),"E1":float(c[1]),"tau":float(tau),"rmse":rmse,
              "state_equation":"qdot = strain_rate - q/tau",
              "stress_equation":"stress = E_inf*strain + E1*q"}
        if best is None or rmse<best["rmse"]: best=cand
    return best

def compare(samples,dt=.01,required_ratio=2.0):
    cut=int(.7*len(samples)); train=samples[:cut]
    m0=fit_memoryless(train); m1=fit_one_state(train,dt)
    ratio=m0["rmse"]/m1["rmse"]
    return {"memoryless":m0,"one_state":m1,"rmse_improvement_ratio":ratio,
            "latent_state_required":ratio>required_ratio,
            "claims_state":CLAIMS_STATE,"execution_status":EXECUTION_STATUS}

def main():
    r=compare(generate(n=1200,noise_std=.08))
    print(r)

if __name__ == "__main__": main()
