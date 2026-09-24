# Claude Code prompts

Source: Claude Code cloud session on this repository, 2026-09-24 (reviewer called Opus; the Codex implementer is called Astra). User messages are reproduced verbatim in chronological order; typos are preserved. The submission log `output/prompts.md` carries the same entries.

## Claude Code prompt 1: research best practices, improve, log prompts, push to main

Issued to Claude Code (cloud session) on 2026-09-24, on the repository as published at v0.3.0.

~~~~text
okay we work on this and we improve this
You are doing wide research on best practices regarding this type of schemas and if something is wrong you flag it to me
Try to think in the way I would in the ideal conditions and honestly do log of MY prompts in the correspomding folder
push everything to main
~~~~

## Claude Code prompt 2: flag generic ideas; issues for Codex

Sent while prompt 1 was being worked on, in the same session.

~~~~text
also, please flag generic things! I am supposed to be the source for non-generic ideas!
Also please feel free to create comments for codex and leave comments for codex in the issues for the repo
For such things indicate yourself as Opus and indicate Codex as Astra
~~~~

## Claude Code prompt 3: generic items should become discussions

Sent while prompt 1 was being worked on, in the same session. The first line repeats prompt 2.

~~~~text
also, please flag generic things! I am supposed to be the source for non-generic ideas!

I meant when you notice that something is generic please reach out with DISCUSSION how to fix and improve such things to me
~~~~

## Claude Code prompt 4: current setup

Transcribed from the Claude UI; text is preserved, but the UI does not establish exact original newline placement.

~~~~text
Hello, it's Veronica
I would like to have a breif of what is your and gpt's current set up, decisions and reasoning on that in bullet points
~~~~

## Claude Code prompt 5: assurance design

Transcribed from the Claude UI; text is preserved, but the UI does not establish exact original newline placement.

~~~~text
Auditing AI, or auditing with AI.
Both! 
We add "integrity" boolean, "completeness" from 0 to 1 estimation, source_reliability from low to high, method, validation_sample_size, estimated false positive rate, estimated_false_negative_rate and overall confidence in bayesian sense!
Please design this you guys have 10 minutes left than we submit
~~~~

## Claude Code prompt 6: division of work

~~~~text
hey, codex catched the implementation, you are the thinker here
~~~~


## Claude Code prompt 7: read-only inspection and prompt logging

Issued to a new Claude Code cloud session on 2026-09-24, after v0.5.0 was published on `main`. The session was asked to make no changes beyond this log entry. Copied from the session's user-message record, newlines preserved.

~~~~text
you are read only Fable
check what s going on in the repo, fill out my prompt to the prompt log and return with the result of inspection
~~~~

## Additional Claude prompts relayed in GitHub issue #2

Source: Claude's issue comment https://github.com/madokamemika/automated-auditor-schema/issues/2#issuecomment-5817840059. Text as supplied there; chronology relative to the separate Fable session is not independently established.

~~~~text
would you think the false negative/positive have sense as metrics here?
~~~~

~~~~text
Each of the 200 responses gets a label (refusal or not) from a judge. Compare those labels with trusted human labels and you get a real confusion matrix, and false positive and false negative rates are the standard, meaningful summary of it.

> automated auditor output
!!!!!!!

okay, coordinate deconfusion with codex but i still want agent to express confidence in things
~~~~
