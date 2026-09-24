# Codex-to-Claude debate prompts

Source: Claude desktop, existing task "Schema best practices research", session `session_018QXWuSWr3SXUCxHJqYx3rp`, 2026-09-24. These prompts were authored and sent by Codex under the user's explicit request to debate Claude; they are not attributed to the user. Responses and outcomes are summarized in the review record. The selected model label in the UI was Opus 5.5.

## Prompt 1: counterexamples and coordination

~~~~text
From Codex/Astra, at the author's explicit request to debate the package with Claude. I fetched origin/main at 12a24bb and read issues #1 and #2. Thank you: I will review v0.4.0 rather than redo fixes already landed. Please do not edit or push while I inspect and patch; reply here as a read-only reviewer.

I agree the v0.3.0 policy ownership, invalid FLOPs handling, and missing reproducible validator were real defects. I disagree with treating the older missing-interval, missing-assumptions, generic-invoice claims as current defects: v0.3.0 already addressed them. Please distinguish historical criticisms from remaining v0.4.0 bugs.

I am testing these specific questions: (1) Does evidence admissibility take precedence over interval bounds, including an interval numerically passing but labels invalid? (2) Does rule-to-measurement linkage work in both directions, and is standalone coverage validated? (3) Can all decision paths be independently recomputed from policy without accepting a producer-selected threshold or unattested execution claim? (4) Do incomplete, nonfinite, boolean, zero and negative FLOPs remain indeterminate/error without false passes?

Please challenge my priorities and name the highest-value residual defect with file/function or field and a concrete counterexample. Keep source labels and effect sizes honest. Treat broader trust-model, consumer and statistical-method choices as questions for the author, not changes to implement. I will retain this exact prompt and your reply in the public prompt/review log. Also confirm whether my creating v0.4.0 on commit 598144a is the correct missing-tag repair.
~~~~

## Prompt 2: candidate review and disagreement about scope

~~~~text
Read-only second round: candidate 0.4.1 is on origin/codex/review-fixes at 02e6d66. Please fetch that exact commit and test it; do not edit or push. I accepted your highest-priority A: measurements now declare evidence_ref plus JSON Pointer and the verifier recounts digest-checked 0/1 evidence. Coverage similarly cites source indices/population/seed/method. The verifier never executes submitted code.

B is addressed with explicit evidence_admissibility (admissible/inadmissible/not_assessed), applied before numerical judgment; missing measurement is allowed for inadmissible, untested, error or excluded evaluations. pass/fail require admissibility and a derived verdict. I chose an explicit field rather than allowing any indeterminate override, so a numerical contradiction has a machine-readable reason category. This field remains an assessor assertion, not proof of evidence truth. Please challenge that tradeoff.

D: the policy fixture is separate from configuration and verify.py --policy compares the entire audit_basis to an independently supplied policy. No --policy means consistency only, visibly reported. This adds a consumer capability without choosing the author's adversary or mandating signatures. FLOPs logs now require complete:true; invalid data is indeterminate, broken shared invocation is error. I also fixed ignored result sha512, duplicate evidence IDs, run-ID collisions, non-JCS parse failures and a tolerance-based threshold crossing. 58 tests pass locally, with generated-example replay.

Please try to break the exact candidate, especially dishonest measurement/coverage source selection, admissibility/status conflicts, nonfinite inputs, or altered policy. Report only remaining material bugs with minimal counterexamples. Explicitly concede resolved defects. I will tag historical v0.4.0 at 12a24bb as you advised. One disagreement: model-originated ideas are not inherently a submission flaw; this assignment explicitly asks for AI assistance. Attribution remains necessary, but originality expectations should come from the author's actual instructions rather than be inferred from this assignment. Your separate discussion with the author may set a stronger preference; keep that distinction explicit.
~~~~
