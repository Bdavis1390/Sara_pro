"""Worldshepherd constitutive discovery v0.5: bounded competitive latent dynamics."""
from dataclasses import dataclass
import math, hashlib, json

@dataclass(frozen=True)
class Hypothesis:
    name:str; decay:float; drive_eps:float; drive_rate:float; nonlinear:float=0.0

FAMILIES=[
 Hypothesis("relax_rate",2.0,0.0,1.0,0.0),
 Hypothesis("relax_strain",2.0,1.0,0.0,0.0),
 Hypothesis("nonlinear_relax_rate",2.0,0.0,1.0,0.5),
]

def step(h,z,eps,rate,dt):
    dz=-h.decay*z+h.drive_eps*eps+h.drive_rate*rate-h.nonlinear*z**3
    return z+dt*dz

def safe_experiment_grid(strain_max=.06,freq_max=5.0,temp_bounds=(273.15,333.15)):
    for a in (.01,.03,.045,.06):
      if a>strain_max: continue
      for f in (.1,.5,1.,2.,5.):
       if f>freq_max: continue
       for T in temp_bounds: yield {"amplitude":a,"frequency_hz":f,"temperature_k":T}

def trajectory(h,e,n=300,dt=.01):
    z=0.; out=[]
    for i in range(n):
      t=i*dt; w=2*math.pi*e["frequency_hz"]
      eps=e["amplitude"]*math.sin(w*t); rate=e["amplitude"]*w*math.cos(w*t)
      z=step(h,z,eps,rate,dt); out.append(z)
    return out

def discriminate(a,b,**bounds):
    best=None
    for e in safe_experiment_grid(**bounds):
      x=trajectory(a,e); y=trajectory(b,e)
      score=sum((u-v)**2 for u,v in zip(x,y))/len(x)
      q={**e,"disagreement":score,"execution_status":"PROPOSED_NOT_EXECUTED"}
      if best is None or score>best["disagreement"]: best=q
    return best

def signed_manifest(payload,previous_hash=None):
    body={"schema":"WS-CD-v0.5","payload":payload,"previous_hash":previous_hash,
          "physical_execution":"PROPOSED_NOT_EXECUTED","claims":"SIMULATED ONLY"}
    body["sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
    return body
