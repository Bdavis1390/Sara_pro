# Observability–Controllability Operating Envelope

## 1. The synthesis

Worldshepherd's research has separately developed:

- latent-state inference;
- identifiability;
- epistemic action;
- empowerment;
- semantic information;
- safety governance.

Control theory reveals that these are not unrelated.

### Observability
Can internal or environmental state be reconstructed from available measurements?

### Controllability
Can available actions drive that state to materially different conditions?

### Dual control
Can an action both:
- direct the system toward a task objective;
- probe the system so future state estimates improve?

This is the bridge from reasoning to closed-loop agency.

## 2. Classical linear form

For:

x_(t+1) = A x_t + B u_t
y_t = C x_t

controllability depends on whether action through B and system dynamics A can span the relevant state space.

Observability depends on whether outputs through C and dynamics A carry enough information to reconstruct state.

For linear time-invariant systems, the two are algebraic duals under transposition.

The Worldshepherd extension is conceptual rather than claiming every domain is linear.

## 3. The four operating regimes

### High observability / high controllability

The system can estimate and influence the state.

Appropriate posture:
- closed-loop control;
- feedback;
- bounded optimization;
- runtime safety monitoring.

### High observability / low controllability

The system can diagnose but cannot strongly intervene.

Examples:
- historical evidence;
- remote astronomical observations;
- many medical states without effective intervention.

Appropriate posture:
- monitor;
- forecast;
- inform human action;
- avoid pretending observation implies control.

### Low observability / high controllability

This is the highest-risk quadrant.

The system can materially alter a state it cannot estimate well.

Examples can include:
- high-power actuator with degraded sensors;
- autonomous software mutation without sufficient telemetry;
- invasive intervention under uncertain diagnosis;
- cybersecurity response that can destroy evidence while compromise state is unclear.

Appropriate posture:
- PRIME blocks or derates action;
- increase sensing;
- choose reversible probes;
- apply safety shield;
- require human approval.

### Low observability / low controllability

The system neither knows nor controls the state well.

Appropriate posture:
- characterize;
- collect evidence;
- report uncertainty;
- avoid confident action.

## 4. Belief-state world model

Under partial observability, the agent should not equate observation o_t with state s_t.

Maintain:

b_t(s) = P(s_t=s | o_1:t, a_1:t-1)

Then:

b_(t+1)
=
BayesUpdate(b_t, a_t, o_(t+1)).

A belief state is a probability distribution over possible states.

Under a specified POMDP model it can summarize the relevant action-observation history for decision making.

This is directly aligned with the latent-consciousness lesson:

observed behavior is evidence about state,
not state itself.

## 5. Dual control

Ordinary control asks:

"What action best moves the system toward the target?"

Pure epistemic action asks:

"What action best reduces uncertainty?"

Dual control asks:

"What action best balances both?"

Thus:

U(a)
=
task_value(a)
+
lambda_e * epistemic_value(a)
-
risk(a)
-
cost(a).

The same action may alter both the physical system and the future information available about it.

## 6. Worldshepherd safety invariant

For consequential state variable x_i, define:

O_i = validated observability
C_i = potential controllability
A_i = authorized controllability
S_i = safety-filtered controllability.

The proposed governance constraint is:

S_i <= A_i <= C_i

and for high-consequence actions:

A_i should not materially exceed validated O_i without an independent safety shield or human-approved exception.

This is a design invariant, not a theorem of control theory.

## 7. Consciousness application

State:
latent consciousness / arousal / network organization.

Observations:
- behavior;
- EEG;
- fMRI;
- PCI;
- connectivity;
- criticality;
- non-equilibrium measures.

Controls/perturbations:
- sensory stimulation;
- pharmacology;
- TMS;
- DBS in clinical contexts.

The correct design question becomes:

**How observable is the state before and during the intervention, and how controllable is the target network?**

A high-power intervention under poor state estimation is exactly the low-O/high-C hazard regime.

## 8. Translation application

State:
best-supported source reading / semantic reconstruction.

Observations:
witnesses, paleography, apparatus, parallels.

Control:
we cannot control the ancient source state.

Therefore translation is usually:
high/medium observability + near-zero controllability.

Its epistemic actions are collection actions:
find new witness, join fragment, compare parallel.

This explains why generating more fluent prose cannot solve an identifiability problem.

## 9. Cybersecurity application

State:
host/network compromise state.

Observations:
alerts, process graphs, network flow, identity telemetry.

Controls:
isolation, credential reset, process termination, reimage.

Low observability + high destructive controllability is dangerous because response can erase evidence or interrupt legitimate operations.

Preferred policy:
increase observability first or use reversible isolation/shielding.

## 10. AGI implication

A generally capable agent needs at least four distinct internal models:

1. **belief model** — what world state might be true?
2. **observation model** — what does each sensor/output reveal?
3. **transition/control model** — what does each action change?
4. **safety/authorization model** — what changes are permitted?

Without this decomposition, the agent can confuse:
- seeing with knowing;
- acting with controlling;
- controlling with understanding;
- capability with authorization.

## 11. Major systems principle

The research path now has a compact closed-loop statement:

**Know the state as well as possible.
Know what you cannot know.
Know what your actions can change.
Use actions to learn when needed.
Never let control outrun observability and governance.**
