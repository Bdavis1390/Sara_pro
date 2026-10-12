# WS-QX 0.1 Publication Acceptance Gate

Before merge/publication to protected main:

- Required Test and Build succeeds on the exact head.
- CodeQL required gate succeeds on the exact head when applicable.
- Existing SARA verified-local/resilience/closure gates remain green.
- WS-QX tests demonstrate fail-closed internal, physical, and external promotion.
- WS-SEMCAP tests demonstrate that reduction cannot hide utility, critical-event, reconstruction, or provenance failure.
- Claims matrix remains explicit and conservative.
- No DV019, physical, UAS-flight, external, certification, or partner-validation claim is introduced without evidence.

If any required gate fails, publication to main is blocked and the branch remains a release candidate.
