# tripwire

**Your agent wants the light green. tripwire fires before it can claim done.**

tripwire fuses Nelson's agent-integrity family — deterministic, zero-LLM,
local-first judges — into one product any agent host can mount, in three
layers with three different trust properties:

| Layer | Mechanism | Trust property |
| --- | --- | --- |
| **Enforcement** | Claude Code hooks (Stop / PreToolUse) | Harness-executed; the agent cannot skip it |
| **Query** | MCP server | Convenience and observability; never enforcement |
| **Method** | Skills | Teaches honest agents the pre-registration discipline |

The founding rule (from [charterlock](https://github.com/taipei49314/charterlock)):
**an exam the examinee wrote is not an exam.** Enforcement lives outside the
agent's trust domain; judges are deterministic and replayable; tripwire pins
judges by git tag and never edits their logic ([SPEC.md](SPEC.md) §2).

## Status

**M0 — greenwash stop gate.** When the agent tries to finish a turn, the
vendored [greenwash](https://github.com/taipei49314/greenwash) (pinned
`v0.1.47`) checks HEAD..worktree for verification-layer tampering — weakened
assertions, new skips, rewritten goldens, relaxed CI — and blocks the stop
with the finding fed back to the agent. Fail-closed: a missing, crashed, or
hung judge blocks too.

Honest scope note (greenwash's own warning): a local hook is an author-side
convenience. Merge-level enforcement is a **required status check**; tripwire
does not pretend otherwise.

## Install (M0)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/install.ps1
python -m unittest discover -s tests -t .
```

The installer vendors the judge at its pin (never patched), self-checks it,
and prints the Stop-hook snippet to paste into a target repo's
`.claude/settings.json`. This repo dogfoods its own gate via
[.claude/settings.json](.claude/settings.json).

## Family map

| Judge | Layer | Milestone |
| --- | --- | --- |
| greenwash | hooks | **M0 (landed)** |
| walkaround · phaseledger | hooks | M1 |
| trust-meter · nullbench · unasked · RepoPassport | MCP | M2 |
| T-series pre-registration method | skills | M3 |

Roadmap and frozen acceptance criteria: [SPEC.md](SPEC.md).

## License

MIT. The vendored judges keep their own licenses.
