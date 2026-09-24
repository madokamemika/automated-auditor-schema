# Task: Automated Auditor Output Schema MVP

We have ~1 hour total. Build a compact, defensible MVP data schema for the output of an automated auditor.

## Assignment

"Use AI tools to produce a data schema for an automated auditor output. The schema could potentially include elements recording the information processed by the auditor, the conclusions reached, components establishing the information integrity of the object, and so forth. This task is deliberately underspecified to evaluate your ability to work through unknowns and produce something useful or illustrative within a short period of time.

Turn in all prompts issued to the AI tool(s) along with the final result."

## Design goal

Do NOT produce a generic collection of fields.

Treat an audit result as a machine-readable, verifiable chain:

subject
→ audit basis / requirement
→ procedure
→ evidence
→ observation
→ evaluation
→ overall conclusion
→ attestation

Core design principle:

> An automated audit output should encode not merely conclusions, but a traceable evidence-to-judgment chain.

The result should be small enough to plausibly design in one hour, but rigorous enough to show awareness of provenance, evidence integrity, uncertainty, and reproducibility.

## Prior-art inspiration

Use NIST OSCAL Assessment Results as conceptual inspiration, especially:
- assessment subject
- observations
- findings
- evidence
- origins / provenance
- assessment methods
- machine-generated evidence

Also borrow useful ideas from:
- SLSA / in-toto provenance: subject digest, materials, invocation, verifier, attestations
- OpenTelemetry-style execution/event provenance if useful

Do NOT attempt full OSCAL compatibility.

## Desired top-level structure

Something approximately like:

{
  "schema_version": "...",
  "metadata": {},
  "subject": {},
  "audit_basis": {},
  "execution": {},
  "evidence": [],
  "evaluations": [],
  "conclusion": {},
  "attestation": {}
}

You may improve this structure if there is a good methodological reason.

## Important semantics

### subject
Bind the result to the exact audited object/version, preferably using a cryptographic digest.

### audit_basis
Make explicit what standard, policy, control, requirement, or claim is being tested.

An audit conclusion without a normative basis is underspecified.

### execution
Record what automated auditor ran, its version, run ID, relevant parameters, environment, and timestamps.

### evidence
Evidence is first-class.

Each evidence item should be identifiable and ideally include:
- id
- type
- source/locator
- acquisition method
- acquisition time
- collector
- cryptographic digest
- optional content/metadata

### evaluation
This is the core object.

Each evaluation should connect:
- requirement_ref
- procedure/method
- evidence_refs
- observations
- assessment/result

Do not collapse observations and conclusions.

Distinguish:

source data
→ observation
→ inference/evaluation
→ judgment

We do NOT want hidden model chain-of-thought. We want externally inspectable claims and references.

### status
Support at least:
- pass
- fail
- indeterminate
- not_applicable
- not_tested

"Indeterminate" is especially important: missing evidence should not silently become pass or fail.

### conclusion
Aggregate evaluations rather than duplicating them.

### attestation
Represent integrity/provenance of the result.

Potential fields:
- subject digest verification
- evidence set digest
- result digest
- signature
- signing key identifier
- generated_at

The aim is to establish not just "bits did not change" but that this result corresponds to this subject, evidence set, policy, and execution.

## Deliverables

Create four polished files:

1. `README.md`
   - ~1–1.5 pages maximum
   - purpose
   - design requirements
   - conceptual model
   - key design choices
   - scope / limitations
   - brief note on prior art

2. `auditor-result.schema.json`
   - JSON Schema Draft 2020-12
   - valid JSON Schema
   - compact rather than encyclopedic
   - use `$defs` where it improves readability
   - meaningful required fields
   - enums where appropriate
   - IDs/references should be structurally clear
   - roughly 200–350 lines is fine; do not bloat for its own sake

3. `example-result.json`
   - realistic valid example
   - include at least:
     - one PASS evaluation
     - one FAIL evaluation
     - one INDETERMINATE evaluation due to unavailable/insufficient evidence
   - references should resolve coherently
   - demonstrate evidence → observation → assessment traceability

4. `prompts.md`
   - preserve all prompts supplied to AI tools
   - organize chronologically
   - do not fabricate prompts that were not actually issued
   - leave a clearly marked place where additional Codex prompts can be appended

## Quality bar

The evaluator should be able to understand the design in 2–3 minutes.

The artifact should feel like a small proposed interchange standard, not an essay and not an AI-generated field dump.

Prioritize:
- traceability
- provenance
- explicit audit criteria
- evidence integrity
- uncertainty
- machine readability
- minimalism

Avoid:
- huge taxonomy
- full OSCAL implementation
- complex PKI
- excessive risk-management machinery
- model chain-of-thought
- speculative fields with no clear purpose
- long prose

## Validation

Before finishing:
- validate `auditor-result.schema.json` as JSON
- validate `example-result.json` against the schema
- check every `*_ref` in the example points to an existing ID where applicable
- inspect for duplicated or semantically ambiguous fields
- make README terminology exactly match schema terminology

If you identify a materially better architecture while implementing, use it, but document the reason briefly in README.

## Handoff instructions

Implement and validate immediately rather than spending the time budget on further research. Write the four final deliverables listed above into `output/`. That directory is intentionally empty in this handoff package. Use `references/oscal-notes.md` for conceptual background and copy the actual prompt history from `prompts/chatgpt-prompts.md` into the final `output/prompts.md`, appending later prompts verbatim.

## Uncertainty model (added)

Do not use a bare `confidence` number. Represent uncertainty in three checkable places:

1. `observation.measurement` (optional): value, unit, and `interval`
   {lower, upper, level, method, sample_size}. Only for quantitative observations.
2. `observation.coverage` (optional): {examined, population, sampling, seed}.
3. `evidence.reliability` (required enum):
   independently_collected | operator_supplied | attested.

Verdicts are derived, not asserted. `assessment.decision_rule` =
{threshold, comparator, basis: point_estimate | interval_bounds}.
With interval_bounds: pass if the whole interval satisfies the comparator,
fail if none of it does, indeterminate if it straddles the threshold.

`observation.claim` must be a checkable proposition that includes the observed
value, not a label.

Two sources of `indeterminate` must both appear in the example:
- evidence unavailable (no measurement possible)
- evidence present but interval straddles threshold

Example file: use an AI-relevant subject (a model checkpoint audited against a
deployment policy). Three evaluations:
- binary config/policy check → pass or fail, no measurement
- hazardous-request refusal rate, 188/200 = 0.940, Wilson 95% [0.898, 0.965],
  threshold >= 0.95 → indeterminate
- training compute declaration, logs not provided → indeterminate

README must include one line: "Verdicts are derived from observations via
explicit decision rules; the auditor never asserts confidence it cannot justify."

Implementation clarification: retain both pass and fail examples from the original quality bar, so the two binary checks plus the two indeterminate checks yield four evaluations. Display interval bounds to three decimals in prose; preserve full precision in JSON for verification. The subject is an embedded synthetic toy checkpoint, not a claim about a real model.
