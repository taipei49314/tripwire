---
name: preregister
description: >
  T-series pre-registration for tripwire work. Write the claim and predicted
  verdict before running any judge. Use when the user runs /preregister, says
  freeze first, no backfill, or P1-P4.
---

# Preregister

You are not allowed to discover the answer and then pretend you predicted it.

## Before any judge

Write, in the working tree or the reply, all of:

1. **Claim** — what this change is supposed to do
2. **Predicted verdicts** — Stop / PreToolUse / MCP, named
3. **Must-not-move** — which existing frozen criteria stay green

Then run the judges. Do not edit the prediction after seeing output.

This is **claim before measure**. **no backfill.**

## Mapping onto tripwire

| You are about to | Preregister |
| --- | --- |
| finish a turn | walkaround receipt + phaseledger checkpoint + greenwash worktree |
| `git commit` / `git push` | M1-C range |
| query MCP | tool name + expected `isError` |

Use `phaseledger claim` before `measure`. Use `nullbench freeze` before `settle`. Use a walkaround `contract` before `close`.

## Stop

If the measured verdict disagrees with the preregistered prediction, report the miss. Do not weaken SPEC.md to make it match.
