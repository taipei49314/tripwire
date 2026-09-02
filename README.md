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

**M0 — greenwash stop gate (landed).** When the agent tries to finish a turn,
the vendored [greenwash](https://github.com/taipei49314/greenwash) (pinned
`v0.1.47`) checks HEAD..worktree for verification-layer tampering — weakened
assertions, new skips, rewritten goldens, relaxed CI — and blocks the stop
with the finding fed back to the agent. Fail-closed: a missing, crashed, or
hung judge blocks too.

**M1-R — walkaround receipt gate (landed).** The same Stop is a
done-claim. After greenwash allows, tripwire requires a walkaround
`ADMITTED` receipt (`walkaround hook`). No receipt is `BYPASSED`. A
`REFUSED` / `INCOMPLETE` receipt is blocked with the verdict passed
through. Vendored [walkaround](https://github.com/taipei49314/walkaround)
@ `v0.4.1`.

**M1-C — submit gate (landed).** PreToolUse matcher `Write|Edit|Bash`
runs `hooks/tripwire_pretooluse.py`. Commit scans HEAD..worktree. Push
scans unpushed commits, including `--all` / `--mirror` / `src:dst` /
`--tags` (M1-C2). Write/Edit of production paths need `plan: ADVANCED`
unless the path is `.phaseledger` / `.walkaround` / `.charterlock`
(M1-W). `git commit --no-verify` still hits this harness gate (H1);
a human terminal `--no-verify` does not.

**M1-P — phaseledger checkpoint (landed).** After greenwash and
walkaround allow, Stop requires `.phaseledger/ledger.json` that
`phaseledger verify` accepts **and** `status` shows at least one
`ADVANCED` phase. Empty init is not a checkpoint. Skip-ahead fails
verify. Vendored [phaseledger](https://github.com/taipei49314/phaseledger)
@ `v0.6.0`.

**M1-K — charterlock (landed).** After phaseledger, Stop requires a
`.charterlock/` tree and vendored [charterlock](https://github.com/taipei49314/charterlock)
@ `v0.1.0` `measure` exit 0 (`CHARTER_SPLIT`). Missing charter is
`NO_CHARTER`. Collapsed / incomplete verdicts pass through.

**M2 — MCP query plane (landed).** `python mcp/tripwire_mcp.py`
exposes six tools as JSON-RPC over stdio (M2.1 adds `repo.passport`).
Convenience, never a hook. `repo.investigate` defaults to unasked
`doctor`; `mode=full` runs `investigate`. Live nullbench freeze
requires typer/numpy (`pip install -e vendor/nullbench`). Missing
judges fail closed.

**M3 — skills (landed).** `skills/preregister`, `skills/adversarial-verify`,
`skills/verdict-format`. Method only; hooks do not read them.

**H1 — `--no-verify` honesty.** `python hooks/tripwire_honesty.py`
states the residual: Claude PreToolUse still sees `git commit --no-verify`;
a human CLI `--no-verify` skips git hooks and tripwire (tripwire is not
a git hook). Merge enforcement is a required status check. Not solved.

**M4 — required status check (criteria frozen, not landed).** SPEC
CI1–CI11: vendored greenwash @ v0.1.47 on the PR/push range as GitHub
job `tripwire`. Session gates stay off CI. A workflow file is not
enforcement; the owner must apply `.github/required-ruleset.json`.

Honest scope note (greenwash's own warning): a local hook is an author-side
convenience. Merge-level enforcement is a **required status check**; tripwire
does not pretend otherwise.

## Install (M0 + M1 + M2)

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
| greenwash | hooks | **M0** + **M1-C** |
| walkaround | hooks | **M1-R** |
| phaseledger | hooks | **M1-P** |
| trust-meter · nullbench · unasked | MCP | **M2** + **M2.1** |
| RepoPassport | MCP | **M2.1** |
| charterlock | hooks | **M1-K** |
| T-series pre-registration | skills | **M3** |

Roadmap and frozen acceptance criteria: [SPEC.md](SPEC.md).

## License

MIT. The vendored judges keep their own licenses.
