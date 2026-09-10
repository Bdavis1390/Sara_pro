# WS-NSB v1.7 — G12 Adaptive Lorentz-Curl Control Abstraction

## Purpose

G12 is the first closed-loop control gate in the WS-NSB chain. It places a deterministic bounded feedback controller around the validated G10 nonlinear 2D periodic incompressible resistive-MHD plant.

The control input is **not a claimed hardware field**. It is an abstract, prescribed basis for the vorticity source `curl(f_EM)/rho`. That abstraction allows the control algorithm, safety bounds, zero-control parity, wrong-sign red-team behavior, and deterministic evidence path to be tested before any real coil/electrode/metasurface mapping is asserted.

## Controller

Three fixed low-order actuator basis functions are used. At each timestep the controller projects the measured vorticity state onto those modes and applies bounded negative feedback:

```text
c_k = <omega,g_k>/<g_k,g_k>
u_k = clip(-K*c_k, -u_max, u_max)
s_omega = sum_k u_k*g_k
```

The commands are held over one midpoint-RK2 step and then recomputed from the new state.

## Plant equation

The underlying G10 vorticity equation is augmented only by the abstract control source:

```text
domega/dt = -u.grad(omega) + B.grad(j) + nu*laplacian(omega) + s_omega
da/dt     = -u.grad(a) + eta*laplacian(a)
```

## Acceptance evidence

The default gate requires:

- zero-control evolution matching the unmodified G10 plant to <= 1e-12 combined L2;
- every command remaining inside the declared command bound;
- >= 5% reduction in targeted vorticity modal energy versus the identical uncontrolled case;
- >= 2% reduction in final enstrophy versus the identical uncontrolled case;
- a wrong-sign controller producing a worse targeted-mode outcome than the correct feedback law;
- velocity and magnetic divergence <= 1e-10;
- nonzero finite control effort and a state-dependent command change over the trajectory;
- deterministic report verification.

## Scientific boundary

G12 demonstrates a **simulated control algorithm** against an abstract Lorentz-force-curl actuator kernel. It does not establish that any particular real electromagnetic hardware can generate the commanded kernel.

Mapping real coil currents, electrode voltages, RF/metasurface states, geometry, conductivity, skin depth, plasma response, or actuator power into this control basis is a later validation problem.

## Claims control

G12 remains `SIMULATED_ONLY`. It explicitly rejects claims of physical actuator mapping, laboratory adaptive EM control, compressible/3D MHD, Hall/two-fluid/kinetic/plasma validation, propulsion, shielding, stealth, cloaking, operational capability, or finite-time Navier-Stokes singularity reproduction.
