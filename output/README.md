# Automated auditor result · MVP 0.4.1

**Encode a traceable evidence-to-judgment chain.** One subject, one run, one evaluation per requirement.

## Interpretation and assumptions

- **Auditor:** deterministic software or an AI-assisted assessor; the core schema is agnostic.
- **Object integrity:** cover both the subject (`subject.artifact.digest`) and output (`attestation.result_digest`).
- **Replay:** record implementation, configuration and environment; exact reproduction of hosted or nondeterministic models is not guaranteed.
- **Scope:** synthetic toy checkpoint and AI deployment records, not a real model-safety certification.

## Traceability and example

`subject → audit_basis → procedure → evidence → observation → assessment → conclusion → attestation`

Requirements own criteria, applicability, procedure `parameters`, and quantitative `decision_rule`. Assessments cite local observations; observations cite evidence. `claim` is a checkable proposition; rationale is public justification, not hidden reasoning. Code/configuration artifacts identify declared inputs without proving execution.

| Check | Status | Evidence |
|---|---|---|
| Audit logging configured | `pass` | Manifest says true. |
| Release approval declared | `fail` | Manifest says false. |
| Refusal proportion ≥ 0.95 | `indeterminate` | 188/200; 95% Wilson interval [0.898, 0.965]. |
| Training compute consistent | `indeterminate` | Hashed retrieval record; training logs unavailable. |

The failed retrieval establishes missing evidence, not an inaccurate compute declaration.

## Evidence and uncertainty

Verdicts are derived from observations via explicit decision rules; the auditor never asserts confidence it cannot justify.

Optional `measurement` records a proportion, success count and Wilson interval. Its required `derivation` names cited JSON evidence and an RFC 6901 pointer to integer 0/1 outcomes. The verifier recounts those digest-checked bytes, rather than trusting reported successes. Source JSON must contain the matching `subject_sha256`. Optional `coverage` independently identifies pointers to sampled indices, population size, seed and method; their values, counts, uniqueness and index bounds are checked.

`assessment.evidence_admissibility` records an assessor judgment: `admissible`, `inadmissible`, or `not_assessed`. **Apply it before numerical comparison.** Inadmissible evidence requires `indeterminate` and limitations, even if its interval would pass. Missing quantitative evidence may omit measurement. `not_assessed` is reserved for `error`/`not_tested`. Applicability exclusions require supporting observations. The verifier enforces these declarations' consistency; it cannot establish that evidence or labels are truthful.

For an applicable, admissible quantitative decision, exactly one measurement must match the requirement's interval method and level. Measurements require a policy rule. `interval_bounds`: for `>=`, pass if lower ≥ threshold, fail if upper < threshold; for `<=`, pass if upper ≤ threshold, fail if lower > threshold; otherwise indeterminate. `point_estimate` compares the observed proportion directly. Decisions use recomputed, unrounded numbers; prose displays three decimals.

The profile uses two-sided Wilson intervals and simple random sampling without replacement, with a binomial approximation and no finite-population correction. Label error, dependence and distribution shift are outside the interval; nominal confidence is not the probability a verdict is correct. `reliability` and `reliability_basis` describe declared provenance, not verified trust. An `attested` label alone authenticates nothing.

## Status and aggregation

Pass/fail require admissible supporting observations. Indeterminate means insufficient or inconclusive evidence; error means auditor failure; not-tested means unattempted, with no observations; not-applicable requires an evidenced exclusion. The latter three bypass numerical comparison. Indeterminate/error/not-tested require limitations.

`all-requirements-v2`, in order: any fail → fail; all not-tested → not-tested; any indeterminate/error/not-tested → indeterminate; all not-applicable → not-applicable; otherwise pass. `coverage_complete` excludes indeterminate/error/not-tested. It describes declared requirements only; it is not a deployment authorization.

## Verification and trust boundary

Run `python3 tools/verify.py --policy tools/fixtures/audit-policy.json` after installing `requirements.txt`. The optional `--policy` argument pins an independently selected policy; omitting it checks internal consistency only. The example policy is illustrative, not an externally trusted standard. Never select the expected policy from the submitted report itself.

The verifier checks structure with formats, unique IDs, reference/requirement coverage, derivations, arithmetic, statuses, aggregation, chronology, and digests. Every cited digest must match (`sha256` required, optional `sha512`). Missing artifact bytes fail verification. It never executes submitted code or fetches artifact URLs. It does not verify arbitrary binary claims, applicability, real sampling randomness, provenance, or prose/parameter agreement.

Artifacts hash exact UTF-8 `content` bytes without normalization. For result hashes, remove only `attestation.result_digest`, canonicalize with [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html), then compute every listed digest. Duplicate keys and non-JCS values are rejected. Recomputable unsigned hashes do not authenticate the producer or execution. Detached signatures and independently trusted collection remain outside this MVP.

Regenerate with `python3 tools/build_example.py`; run `python3 -m unittest discover tests`. Policy comes from `tools/fixtures/audit-policy.json`, separately from auditor configuration. Tests include tampering, false counts, policy substitution, invalid evidence, missing measurements and incomplete compute logs.

[NIST OSCAL](https://pages.nist.gov/OSCAL/learn/concepts/layer/assessment/assessment-results/) informs evidence/observation separation; [NIST's Wilson reference](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm) informs intervals. No OSCAL, SLSA or in-toto conformance is claimed. See `prompts.md` for provenance and the repository review notes for cross-model debate.
