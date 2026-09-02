"""Shared Stop / PreToolUse helpers. No detection logic — that stays in the judge."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

TIMEOUT_SECONDS = 30

_SEGMENT = re.compile(r"(?:&&|\|\||[;\n]|(?<!\|)\|(?!\|))")
_ENV_PREFIX = re.compile(r"^(?:[A-Za-z_][\w]*=\S*\s+)+")
_GIT_OPTS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def tripwire_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def greenwash_src() -> str:
    override = os.environ.get("TRIPWIRE_GREENWASH_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "greenwash", "src")


def walkaround_root() -> str:
    override = os.environ.get("TRIPWIRE_WALKAROUND_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "walkaround")


def phaseledger_root() -> str:
    override = os.environ.get("TRIPWIRE_PHASELEDGER_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "phaseledger")


def trust_meter_root() -> str:
    override = os.environ.get("TRIPWIRE_TRUST_METER_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "trust-meter")


def nullbench_root() -> str:
    override = os.environ.get("TRIPWIRE_NULLBENCH_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "nullbench")


def unasked_root() -> str:
    override = os.environ.get("TRIPWIRE_UNASKED_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "unasked")


def charterlock_root() -> str:
    override = os.environ.get("TRIPWIRE_CHARTERLOCK_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "charterlock")


def repopass_root() -> str:
    override = os.environ.get("TRIPWIRE_REPOPASS_SRC")
    if override:
        return override
    return os.path.join(tripwire_root(), "vendor", "RepoPassport")


def is_git_repo(cwd: str) -> bool:
    try:
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return False
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def read_payload() -> dict | None:
    """BOM-tolerant. None means malformed (fail closed). Empty stdin → {}."""
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def git_commit_push_verbs(command: str) -> frozenset[str]:
    """SPEC M1-C trigger. Subcommand must be exactly commit or push."""
    found: set[str] = set()
    if not command or not command.strip():
        return frozenset()
    for raw in _SEGMENT.split(command):
        s = _ENV_PREFIX.sub("", raw.strip())
        if not s:
            continue
        tokens = s.split()
        git_i = None
        for i, tok in enumerate(tokens):
            base = tok.replace("\\", "/").rsplit("/", 1)[-1].lower()
            if base in {"git", "git.exe", "git.cmd"}:
                git_i = i
                break
        if git_i is None:
            continue
        j = git_i + 1
        while j < len(tokens):
            t = tokens[j]
            if t in _GIT_OPTS_WITH_ARG:
                j += 2
                continue
            if t.startswith("--git-dir=") or t.startswith("--work-tree="):
                j += 1
                continue
            if t.startswith("-"):
                j += 1
                continue
            break
        if j < len(tokens) and tokens[j].lower() in {"commit", "push"}:
            found.add(tokens[j].lower())
    return frozenset(found)


def _git_out(cwd: str, args: list[str]) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip()


def _range_from_rev_list(cwd: str, lines: list[str], tip: str = "HEAD") -> str | None:
    if not lines:
        return None
    oldest = lines[-1]
    parent = _git_out(cwd, ["rev-parse", "--verify", oldest + "^"])
    if parent:
        return f"{oldest}^..{tip}"
    if len(lines) > 1:
        return f"{oldest}..{tip}"
    return None


def unpushed_range(cwd: str, tip: str = "HEAD") -> str | None:
    """oldest^..tip for commits on tip not on any remote-tracking ref."""
    listed = _git_out(cwd, ["rev-list", tip, "--not", "--remotes"])
    if listed is None:
        return None
    lines = [ln.strip() for ln in listed.splitlines() if ln.strip()]
    return _range_from_rev_list(cwd, lines, tip)


def parse_git_push(command: str) -> dict:
    """Flags and refspecs after `git push`. SPEC M1-C2."""
    out = {"all": False, "mirror": False, "tags": False, "refspecs": []}
    if not command:
        return out
    tokens: list[str] = []
    for raw in _SEGMENT.split(command):
        s = _ENV_PREFIX.sub("", raw.strip())
        parts = s.split()
        git_i = None
        for i, tok in enumerate(parts):
            base = tok.replace("\\", "/").rsplit("/", 1)[-1].lower()
            if base in {"git", "git.exe", "git.cmd"}:
                git_i = i
                break
        if git_i is None:
            continue
        j = git_i + 1
        while j < len(parts):
            t = parts[j]
            if t in _GIT_OPTS_WITH_ARG:
                j += 2
                continue
            if t.startswith("-"):
                j += 1
                continue
            break
        if j < len(parts) and parts[j].lower() == "push":
            tokens = parts[j + 1 :]
            break
    skip_next = False
    seen_remote = False
    for t in tokens:
        if skip_next:
            skip_next = False
            continue
        if t in {"--all", "-a"}:
            out["all"] = True
            continue
        if t == "--mirror":
            out["mirror"] = True
            continue
        if t == "--tags":
            out["tags"] = True
            continue
        if t.startswith("-"):
            if t in {"-u", "--set-upstream", "-o", "--push-option", "--repo"}:
                skip_next = True
            continue
        if ":" in t or t.startswith("refs/"):
            out["refspecs"].append(t.split(":", 1)[0] or "HEAD")
            continue
        if not seen_remote:
            seen_remote = True
            continue
        out["refspecs"].append(t)
    return out


def push_ranges(cwd: str, command: str) -> list[str]:
    parsed = parse_git_push(command)
    tips: list[str] = []
    ranges: list[str] = []
    seen: set[str] = set()

    def _add(rng: str | None) -> None:
        if rng and rng not in seen:
            seen.add(rng)
            ranges.append(rng)

    if parsed["all"] or parsed["mirror"]:
        refs = _git_out(cwd, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
        if refs:
            tips.extend(refs.splitlines())
    if parsed["tags"]:
        tag_lines = [
            ln.strip()
            for ln in (_git_out(cwd, ["rev-list", "--tags", "--not", "--remotes"]) or "").splitlines()
            if ln.strip()
        ]
        newest = tag_lines[0] if tag_lines else "HEAD"
        _add(_range_from_rev_list(cwd, tag_lines, newest))
    if parsed["refspecs"]:
        tips.extend(parsed["refspecs"])
    if not tips and not ranges:
        _add(unpushed_range(cwd))
        return ranges
    for tip in tips:
        _add(unpushed_range(cwd, tip.strip() or "HEAD"))
    return ranges


def plan_advanced(cwd: str) -> str:
    """missing | pending | advanced — uses phaseledger status text only."""
    ledger = os.path.join(cwd, ".phaseledger", "ledger.json")
    if not os.path.isfile(ledger):
        return "missing"
    status, text, code = run_phaseledger(cwd, ["status", "--ledger", os.path.join(cwd, ".phaseledger")])
    if status == "error" or code != 0:
        return "missing"
    if "- plan: ADVANCED |" in (text or ""):
        return "advanced"
    return "pending"


def path_is_meta(path: str) -> bool:
    """True for gate dirs. Do not str.lstrip('./') — that strips the leading dot."""
    p = path.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    p = p.lstrip("/")
    meta = (".phaseledger", ".walkaround", ".charterlock")
    wrapped = "/" + p.strip("/") + "/"
    for name in meta:
        if p == name or p.startswith(name + "/"):
            return True
        if f"/{name}/" in wrapped:
            return True
    return False


def run_greenwash(cwd: str, rev_range: str | None = None) -> tuple[str, str]:
    """Invoke vendored greenwash hook-json.

    Returns (status, reason) where status is allow | block | error.
    """
    src = greenwash_src()
    if not os.path.isdir(src):
        return (
            "error",
            "tripwire: vendored greenwash not found (run scripts/install.ps1). "
            "Failing closed: the gate cannot certify this action.",
        )
    argv = [sys.executable, "-m", "greenwash", "check", "--format", "hook-json", "--repo", cwd]
    if rev_range:
        argv.insert(4, rev_range)  # after 'check'
    env = dict(os.environ)
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return (
            "error",
            f"tripwire: greenwash timed out after {TIMEOUT_SECONDS}s. "
            "Failing closed: the gate cannot certify this action.",
        )
    except Exception as err:
        return ("error", f"tripwire: greenwash could not run ({err!r}). Failing closed.")

    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        tail = (result.stderr or result.stdout or "").strip()[-1500:]
        return (
            "error",
            "tripwire: greenwash engine error (exit "
            f"{result.returncode}). Failing closed.\n{tail}",
        )
    try:
        decision = json.loads(out.splitlines()[-1])
    except Exception:
        return (
            "error",
            "tripwire: greenwash produced non-JSON hook output. Failing closed.\n" + out[-1500:],
        )
    if not isinstance(decision, dict):
        return ("error", "tripwire: greenwash hook-json was not an object. Failing closed.")
    if decision.get("decision") == "block":
        reason = decision.get("reason") or "greenwash: blocking finding."
        return (
            "block",
            reason + "\ntripwire: fix the production code; do not weaken the judge.",
        )
    return ("allow", "")


def run_phaseledger(cwd: str, argv: list[str]) -> tuple[str, str, int]:
    """Run vendored phaseledger. Returns (status, text, exit_code).

    status is ok | error. Caller interprets exit_code / text.
    """
    root = phaseledger_root()
    pkg = os.path.join(root, "phaseledger")
    if not os.path.isdir(pkg):
        return (
            "error",
            "tripwire: vendored phaseledger not found (run scripts/install.ps1). "
            "Failing closed: the stop gate cannot certify this turn.",
            2,
        )
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "phaseledger", *argv],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return (
            "error",
            f"tripwire: phaseledger timed out after {TIMEOUT_SECONDS}s. "
            "Failing closed: the stop gate cannot certify this turn.",
            2,
        )
    except Exception as err:
        return (
            "error",
            f"tripwire: phaseledger could not run ({err!r}). Failing closed.",
            2,
        )
    text = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    return ("ok", text, result.returncode)
