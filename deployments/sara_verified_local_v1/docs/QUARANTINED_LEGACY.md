# Quarantined legacy material

The deployment branch excludes legacy scripts and beacon files that perform or describe network scanning, unsolicited broadcasts, third-party activation, self-expansion, or automatic repository mutation.

They are not part of the verified SARA deployment boundary because they lack defined authorization, target ownership, safety controls, test evidence, and rollback procedures. Their exclusion does not erase repository history; prior commits remain available for review.

The verified deployment allows only local, authenticated, auditable operations. Any future external integration requires a separately reviewed connector with allow-listed destinations, authenticated APIs, least privilege, rate limits, explicit approval, and retained evidence.
