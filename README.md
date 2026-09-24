# Automated auditor output schema

A compact, illustrative JSON Schema for a traceable evidence-to-judgment audit result. Current version: **0.4.0**. The example is synthetic, unsigned, and intended for schema exploration, not deployment as a production auditor.

## Submission

- [Design rationale and validation contract](output/README.md)
- [JSON Schema, Draft 2020-12](output/auditor-result.schema.json)
- [AI deployment audit example](output/example-result.json)
- [AI prompt log](output/prompts.md)

The example includes pass, fail, statistical indeterminacy, and indeterminacy caused by unavailable evidence. It embeds the subject, evidence, reference implementation, and configuration so their hashes can be recomputed.

Verify it yourself: `pip install -r requirements.txt && python3 tools/verify.py && python3 -m unittest discover tests`. `tools/build_example.py` regenerates the example from `tools/fixtures/`, so no digest is typed by hand.

## Supporting material

- [Assignment brief and addendum](BRIEF.md)
- [OSCAL reference notes](references/oscal-notes.md)
- [Original supplied prompt history](prompts/chatgpt-prompts.md)
- [Pasted external review](prompts/claude-review-pasted-text.txt)
- [User-supplied Claude prompt history](prompts/claude-prompts.md)
- [Claude Code (Opus) session prompts](prompts/claude-code-prompts.md)
- [Opus best-practices review, idea-origin ledger and open decisions](reviews/2026-09-24-opus-best-practices-review.md)

The prompt log includes the current Codex task messages the user-supplied seven-prompt Claude history, and the Claude Code (Opus) session prompts. Bracketed notes identify pasted responses and file uploads; their original bodies and historical file versions are not reconstructed.

## Known review findings

The v0.3.0 findings are resolved in 0.4.0 and are verified by tests: decision rules are now policy-owned, the reference-code crash is fixed, and the verifier is committed. See the [Opus review](reviews/2026-09-24-opus-best-practices-review.md). Remaining limits:

- Unsigned digests and declared evidence provenance do not authenticate an audit run. Signing is described (in-toto Statement plus DSSE), not implemented.
- Whether a requirement's prose matches its decision rule, and whether evidence is fit for purpose, remain human review questions.
- The embedded reference auditor is a fixture replayed on example inputs, not a production auditor.
- The open design decisions in the review (trust model, AI-as-auditor label error, interval method, naming) await the author.
