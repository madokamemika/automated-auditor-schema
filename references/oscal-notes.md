# Prior-art notes

NIST OSCAL Assessment Results is the main conceptual reference.

Useful concepts:
- assessment subject: what is being assessed
- observation: evidence or fact produced during assessment
- finding: conclusion based on observations
- relevant evidence: supporting artifacts
- origin: actor/tool responsible for information
- assessment method / activity
- back matter / resources
- cryptographic hashes for resource integrity

Main adaptation:
We are not implementing OSCAL. We are using its separation between evidence/observation/conclusion and adapting it for a generic automated auditor.

Additional inspiration:
- SLSA / in-toto: digest-addressed subject, provenance, invocation, verifier, attestation
- OpenTelemetry: run/event provenance and timestamps

Central methodological choice:
Make the evidence-to-judgment chain explicit and independently inspectable.

## Source and status

These notes reproduce the conceptual prior-art summary from the referenced ChatGPT conversation. They are design inspiration, not a verified field-by-field mapping or a claim of OSCAL, SLSA, in-toto, or OpenTelemetry compliance.
