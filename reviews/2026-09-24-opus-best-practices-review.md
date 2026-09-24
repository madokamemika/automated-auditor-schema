# Best-practices review of v0.3.0, and changes in v0.4.0

Reviewer: **Opus** (Claude Code). Prior implementer: **Astra** (Codex). Date: 2026-09-24.
Marks: **VERIFIED** means recomputed or tested in this session; **ASSERTED** means argued from a cited source without a local test.

## Attribution clarification added by Codex after the user's correction

This historical review is preserved below, including its judgments and mistakes. Its suggestion that distinctive ideas ought to originate with the user is not the current framing. The user explicitly clarified that AI tools provide and execute ideas while she controls the work and reads logs. Origin labels below are the reviewer's interpretations of an incomplete record, not independently established authorship. “Generic” or “distinctive” judgments do not establish origin or quality. No historical prompt or quotation has been rewritten to improve the user's apparent contribution.

## 1. Idea-origin ledger: what is generic and what is yours

You asked me to flag generic material, because non-generic ideas are meant to come from you. The prompt log is the only evidence of origin, so this ledger is traced from `output/prompts.md` only.

| Idea in the package | Origin per prompt log | Generic? |
|---|---|---|
| Use OSCAL Assessment Results as the starting point | **You** (ChatGPT prompt 1) | Prior art. The pick is yours; the content is NIST's |
| Reject a flat field bag; demand a method | **You** (ChatGPT prompt 2) | Direction, not a design element |
| Uncertainty as confidence intervals, and the question "confidence of who" | **You** (Claude prompt 2) | The seed is yours. Wilson and the three-way rule are textbook (NIST handbook, ILAC-G8) |
| Cross-model debate; VERIFIED/ASSERTED discipline; verbatim prompt logging | **You** (Claude prompt 5, Codex prompt 5) | Process, and a real differentiator |
| Core thesis "encode a traceable evidence-to-judgment chain" | ChatGPT's reply to prompt 3 ("based on your memory of my usual preferences") | Model-written. **Your wording of it does not appear in any logged prompt** |
| Two sources of `indeterminate` (missing evidence vs. an inconclusive interval) | Claude, derived from your CI prompt | Moderately distinctive |
| Verdicts derived, never asserted; no assessor-confidence score | Claude | Moderately distinctive |
| Recording the failed acquisition (the 404) as hashed evidence | Astra | Distinctive, and the strongest single idea |
| AI-deployment example (refusal rate, compute declaration) | Claude inferred your field | Generic AI-governance examples |
| pass/fail/indeterminate/not_applicable/not_tested | BRIEF (ChatGPT) | Generic; close to XCCDF and SARIF |
| SHA-256 digests, RFC 8785, digest-only seal | BRIEF and Astra | Generic |
| Evidence `reliability` enum | Claude | Generic; a simplified PCAOB AS 1105 |
| **All v0.4.0 changes in section 3** | Opus | **Generic best practice.** None of them is a new idea |

**Flag.** The distinctive ideas in the package came from models (Astra, Claude, ChatGPT), not from logged prompts of yours. Your contributions in the log are direction, process and the uncertainty seed. If the thesis or the AI-governance framing is yours, the log does not show it. Section 4 lists the questions where a non-generic answer from you would change the design; any of them would put your idea on the record.

## 2. What was wrong or weak in v0.3.0

1. **The policy did not own its decision rule.** VERIFIED. `assessment.decision_rule` sat inside the judged output, so the auditor set its own threshold. v0.3.0 admitted this in its known findings. ISO/IEC 17025 §7.1.3 and ILAC-G8 require the rule to be agreed before evaluation. ASSERTED from secondary sources; the ILAC primary PDF could not be read.
2. **The reference code crashed, and could pass a bad total.** VERIFIED. `training_flops: 0` raised ZeroDivisionError, and a negative log total returned `pass`.
3. **The procedure claimed a check the code never ran.** VERIFIED. The refusal procedure said it "verifies report subject_sha256", but the embedded code never compared it. Evidence for a different model would have been scored as this one's.
4. **`execution.parameters` duplicated the configuration artifact.** VERIFIED. Two sources of truth had to be kept equal by hand.
5. **The validation claims could not be reproduced.** VERIFIED. The README said "validation included…" but shipped no scripts.
6. **A single `sha256` field had no algorithm agility.** ASSERTED; see [in-toto DigestSet](https://github.com/in-toto/attestation/blob/main/spec/v1/digest_set.md).
7. **Auditor failure had no status.** ASSERTED. Every mature vocabulary separates "the tool broke" from "the evidence cannot decide": XCCDF `error`, JUnit `<error>`, SARIF `executionSuccessful`, and Inspect `status: error`.
8. **`inspect` diverged from the standard terms.** ASSERTED. NIST SP 800-53A and OSCAL use `EXAMINE`/`INTERVIEW`/`TEST`.
9. **The `$id` URN used an unregistered namespace.** ASSERTED; RFC 8141. It also did not point at the repository.
10. **`result_id` was only locally unique.** ASSERTED. OSCAL uses UUIDs for interchange.

## 3. Changes in v0.4.0, all of them generic best practice (Opus)

- `decision_rule` moved to `requirement`, and now also carries `interval_level` and `interval_method`. The verifier requires a measured observation exactly when the rule exists, and requires its interval to follow the rule.
- `digest` is now a set (`sha256` required, `sha512` optional). `artifact` uses `uri`/`digest`/`media_type`/`content`, mirroring the in-toto ResourceDescriptor.
- Added an `error` status. Aggregation moved to `all-requirements-v2`.
- Procedure methods are now `examine`/`interview`/`test`.
- `execution.parameters` removed; `auditor.implementation` and `auditor.configuration` flattened.
- `result_id` is a `urn:uuid`. Timestamps are pinned to UTC `Z`, because JCS hashes strings as-is. `$id` is a versioned https URL.
- `coverage` now requires `measurement`. `not_tested` forbids observations.
- The reference auditor checks every record's `subject_sha256`, rejects invalid labels and non-positive or non-numeric totals, and returns `indeterminate` instead of crashing.
- Added `tools/verify.py`, which implements the whole README contract, and `tools/build_example.py`, which generates every digest, interval and status. Added 25 tests, including negative and replay tests, and a CI workflow.
- README: authenticity is out of band (an in-toto Statement plus DSSE, following the SLSA VSA pattern), plus VSA and OSCAL status mappings and ILAC decision-rule terms.

## 4. For discussion with you: generic points and open decisions

Per your instruction, generic material comes to you as a discussion, not as a fix Opus decides alone. The v0.4.0 changes in section 3 are correctness and best-practice fixes; each can be reverted if you disagree. The items below are design choices, and none of them has been implemented. Astra has the same list in the repository issues, marked as waiting for your decision.

1. **Trust model.** Who is the adversary: a lab gaming the audit, a compromised auditor, or a careless operator? The answer decides whether signing, independent collection, or evidence expiry comes next. Every generic answer adds all three.
2. **Auditing AI vs. auditing with AI.** The schema is agnostic. If the auditor is an LLM judge, the non-generic question is how judge error enters the uncertainty model. Today the Wilson interval treats labels as ground truth; for an AI auditor that is the weakest assumption in the package.
3. **Who consumes the result**: a deployment gate, a regulator, or the public? This fixes the binary mapping, whether `indeterminate` blocks deployment, and whether results need `valid_until`.
4. **Choice of interval method.** Wilson is Claude's choice, not yours. VERIFIED under our two-sided 95% rule and threshold 0.95: at 188/200 all methods agree (indeterminate; exact hypergeometric [0.900, 0.967]). At **196/200** they diverge: Wilson (0.9497) and Clopper-Pearson (0.9496) say indeterminate, while the exact hypergeometric bound (0.9515) says pass, because the sample is 10% of a finite population of 2000. Clopper-Pearson is the conservative choice if a false pass is the costly error; hypergeometric is the exact model for this sampling design, and it is *less* conservative here.
5. **Naming collision.** OSCAL's `attestations` are assessor statements, while ours is a digest. Renaming it to `integrity` or `seal` would break your BRIEF's structure, so the choice is yours.
6. **Evidence reliability as one axis or several.** AS 1105 separates source (external or internal), acquisition (direct or indirect) and form (original or copy).
7. **Extension point.** Closed objects (`additionalProperties: false`) reject any future field. An `x-` or `annotations` escape hatch would help forward compatibility, at some cost to strictness.

Research sources are cited inline above and in `output/README.md`. Items the research could not verify: the ILAC-G8 primary text, the IIA GTAG 3rd edition, and the tie-point convention for the hypergeometric bound.
