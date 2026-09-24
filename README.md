# Automated auditor output schema

A compact, illustrative JSON Schema for a traceable evidence-to-judgment audit result. Version **0.4.1** includes a synthetic AI deployment example, a verifier, reproducible fixtures and regression tests. It is an unsigned prototype, not a production auditor or safety certification.

## Submission

- [Design rationale and validation contract](output/README.md)
- [JSON Schema, Draft 2020-12](output/auditor-result.schema.json)
- [AI deployment audit example](output/example-result.json)
- [AI prompt log](output/prompts.md)

## Reproduce and verify

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 tools/build_example.py
python3 tools/verify.py --policy tools/fixtures/audit-policy.json
python3 -m unittest discover tests
```

The verifier recounts quantitative evidence, checks policy rules and admissibility, validates referenced artifacts and recomputes all hashes. It never executes code embedded in a submitted report. The example builder and replay tests execute only the repository's fixture auditor. Choose the expected policy independently; without `--policy`, validation establishes internal consistency rather than policy authorization.

## Review fixes and limits

The v0.4.1 fixes bind measured counts and coverage to evidence bytes, allow unusable evidence to remain indeterminate, reject incomplete/invalid compute logs, validate all digest algorithms, and permit consumers to pin a policy. The generator keeps policy separate from auditor configuration.

Still outside scope: authentication of execution, truth of supplied labels, real sampling randomness, arbitrary binary-claim verification and deployment authorization. The admissibility/provenance fields are assessor declarations, not independent guarantees. Broader choices about the adversary, consumer and statistical method remain with the author; see [open design discussion](https://github.com/madokamemika/automated-auditor-schema/issues/2).

## Supporting material

[Brief](BRIEF.md) · [OSCAL notes](references/oscal-notes.md) · [Original prompt history](prompts/chatgpt-prompts.md) · [Supplied Claude history](prompts/claude-prompts.md) · [Claude Code history](prompts/claude-code-prompts.md) · [Earlier pasted review](prompts/claude-review-pasted-text.txt)

The prompt log preserves available inputs and source attribution. Bracketed notes describe pasted responses and historical uploads; missing original content has not been reconstructed. Historical reviews are retained under `reviews/` and must be read against their stated versions.
