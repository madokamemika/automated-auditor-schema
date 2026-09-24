# Automated auditor output schema

A compact, illustrative JSON Schema for a traceable evidence-to-judgment audit result. Current version: **0.3.0**. The example is synthetic, unsigned, and intended for schema exploration, not deployment as a production auditor.

## Submission

- [Design rationale and validation contract](output/README.md)
- [JSON Schema, Draft 2020-12](output/auditor-result.schema.json)
- [AI deployment audit example](output/example-result.json)
- [AI prompt log](output/prompts.md)

The example includes pass, fail, statistical indeterminacy, and indeterminacy caused by unavailable evidence. It embeds the subject, evidence, reference implementation, and configuration so their hashes can be recomputed.

## Supporting material

- [Assignment brief and addendum](BRIEF.md)
- [OSCAL reference notes](references/oscal-notes.md)
- [Original supplied prompt history](prompts/chatgpt-prompts.md)
- [Pasted external review](prompts/claude-review-pasted-text.txt)

The prompt log includes all user messages available from the current Codex task. Original Claude prompts are available only as reported excerpts; full cross-tool prompt completeness is not claimed.

## Known review findings

These are retained limitations of the reviewed v0.3.0 snapshot:

- Normative quantitative rules remain prose; matching assessment thresholds to policy requires separate validation.
- Evidence admissibility needs explicit precedence over numeric threshold decisions.
- A decision rule does not structurally require a measured observation in the reverse direction; coverage consistency also requires semantic validation.
- The embedded reference functions handle the valid example fixture, not arbitrary inputs. Invalid training-compute totals can crash or produce an incorrect pass.
- Unsigned hashes and declared evidence provenance do not authenticate an audit run.

The example and schema were validated before publication, including artifact and RFC 8785 result hashes. The development validation scripts are not included; the validation contract is described in the design README.
