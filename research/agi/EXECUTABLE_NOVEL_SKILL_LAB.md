# Executable Novel-Skill Lab

This directory now contains a minimal executable benchmark substrate for the AGI path.

The key design choice is to make **representation shift a first-class test**.

A task-family-specific reference policy is expected to:
- solve the ordinary switch tasks;
- fail the relabeled task.

That failure is intentional.

If the reference policy also solved the relabeled task because its code knew the hidden mapping, the benchmark would not distinguish memorized interface rules from structural transfer.

A future candidate backend is connected through `ModelAgentBackend`.

The benchmark runner supplies:
- observation;
- available actions;
- explicit persisted state.

The backend must choose an action and receive the consequence.

No benchmark-specific hidden answer is supplied.

## What passing would mean

Passing held-out relabeling after learning the base environment would support:
- online skill acquisition;
- representation-invariant transfer.

It would still not establish AGI.

The result must then generalize across unrelated task families and enter the Competent AGI qualification ledger.
