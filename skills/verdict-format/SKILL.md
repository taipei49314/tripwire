---
name: verdict-format
description: >
  Canonical tripwire verdict vocabulary across Stop, PreToolUse, and MCP.
  Use when the user runs /verdict-format or asks how to read a block reason.
---

# Verdict format

Do not invent scores. Quote these tokens.

## Stop (stdout JSON, process exit 0)

- allow: `{}`
- block: `{"decision":"block","reason":"..."}`

Walkaround session verdicts inside `reason`: `ADMITTED` | `REFUSED` | `BYPASSED` | `INCOMPLETE`.

Phaseledger checkpoint codes inside `reason`: `NO_LEDGER` | `NO_PHASE_ADVANCED` | `VERIFY`.

Greenwash findings stay in `reason` as rule ids (do not rewrite).

## PreToolUse (stdout JSON, process exit 0)

- allow / no decision: `{}`
- deny: `hookSpecificOutput.permissionDecision` = `deny`
- reason field: `permissionDecisionReason`

## MCP (JSON-RPC result, not a hook)

- `isError` false — query succeeded; text is judge stdout
- `isError` true — missing vendor, bad args, or judge non-zero; not a Stop block

MCP is never enforcement. A green MCP call does not authorize Stop.
