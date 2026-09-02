#!/usr/bin/env python3
"""tripwire MCP query plane (M2). Convenience, never enforcement.

JSON-RPC 2.0 over stdio (Content-Length framing; NDJSON also accepted).
Judges are vendored subprocesses; missing vendor is isError fail-closed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks")
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import gate  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "tripwire"
SERVER_VERSION = "m2"
TIMEOUT = 60

TOOL_ORDER = (
    "trust.score",
    "ledger.preregister",
    "ledger.score",
    "receipt.verify",
    "repo.investigate",
)


def _tool_schema(name: str, prop: str, desc: str) -> dict:
    return {
        "name": name,
        "description": desc,
        "inputSchema": {
            "type": "object",
            "properties": {prop: {"type": "string"}},
            "required": [prop],
        },
    }


TOOLS = [
    _tool_schema("trust.score", "target", "trust-meter: score a directory (query, not a gate)"),
    _tool_schema("ledger.preregister", "study", "nullbench freeze --latest (query, not a gate)"),
    _tool_schema("ledger.score", "study", "nullbench settle (query, not a gate)"),
    _tool_schema("receipt.verify", "root", "walkaround verify of a stored admission receipt"),
    _tool_schema("repo.investigate", "workspace", "unasked doctor on a workspace (not a discovery run)"),
]


def _rpc_error(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _rpc_result(id_, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _tool_result(text: str, is_error: bool) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def _run_judge(pythonpath: str, argv: list[str], *, pkg_dir: str) -> tuple[int, str]:
    if not os.path.isdir(pkg_dir):
        return (
            2,
            "tripwire: vendored judge not found (run scripts/install.ps1). "
            "Failing closed: the query plane cannot certify this call.",
        )
    env = dict(os.environ)
    env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, *argv],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return 2, f"tripwire: judge timed out after {TIMEOUT}s. Failing closed."
    except Exception as err:
        return 2, f"tripwire: judge could not run ({err!r}). Failing closed."
    text = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    return result.returncode, text or f"judge exit {result.returncode}"


def _call_tool(name: str, arguments: dict) -> dict:
    if not isinstance(arguments, dict):
        arguments = {}
    if name == "trust.score":
        target = arguments.get("target")
        if not target:
            return _tool_result("tripwire: missing argument target. Failing closed.", True)
        root = gate.trust_meter_root()
        code, text = _run_judge(
            os.path.join(root, "src"),
            ["-m", "trust_meter.cli", "--json", "--no-config", str(target)],
            pkg_dir=os.path.join(root, "src", "trust_meter"),
        )
        return _tool_result(text, code != 0)
    if name == "ledger.preregister":
        study = arguments.get("study")
        if not study:
            return _tool_result("tripwire: missing argument study. Failing closed.", True)
        root = gate.nullbench_root()
        code, text = _run_judge(
            os.path.join(root, "src"),
            ["-m", "nullbench", "freeze", "--study", str(study), "--latest"],
            pkg_dir=os.path.join(root, "src", "nullbench"),
        )
        return _tool_result(text, code != 0)
    if name == "ledger.score":
        study = arguments.get("study")
        if not study:
            return _tool_result("tripwire: missing argument study. Failing closed.", True)
        root = gate.nullbench_root()
        code, text = _run_judge(
            os.path.join(root, "src"),
            ["-m", "nullbench", "settle", "--study", str(study)],
            pkg_dir=os.path.join(root, "src", "nullbench"),
        )
        return _tool_result(text, code != 0)
    if name == "receipt.verify":
        root_arg = arguments.get("root")
        if not root_arg:
            return _tool_result("tripwire: missing argument root. Failing closed.", True)
        root = gate.walkaround_root()
        code, text = _run_judge(
            root,
            ["-m", "walkaround", "--root", str(root_arg), "verify"],
            pkg_dir=os.path.join(root, "walkaround"),
        )
        return _tool_result(text, code != 0)
    if name == "repo.investigate":
        workspace = arguments.get("workspace")
        if not workspace:
            return _tool_result("tripwire: missing argument workspace. Failing closed.", True)
        root = gate.unasked_root()
        code, text = _run_judge(
            os.path.join(root, "src"),
            ["-m", "unasked", "doctor", "--workspace", str(workspace)],
            pkg_dir=os.path.join(root, "src", "unasked"),
        )
        return _tool_result(text, code != 0)
    return _tool_result(f"tripwire: unknown tool {name!r}. Failing closed.", True)


def handle(msg: dict) -> dict | None:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") if isinstance(msg.get("params"), dict) else {}
    if method == "initialize":
        return _rpc_result(
            id_,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            },
        )
    if method == "notifications/initialized" or method == "initialized":
        return None
    if method == "ping":
        return _rpc_result(id_, {})
    if method == "tools/list":
        return _rpc_result(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
        if not isinstance(name, str) or not name:
            return _rpc_result(id_, _tool_result("tripwire: missing tool name. Failing closed.", True))
        return _rpc_result(id_, _call_tool(name, arguments))
    if id_ is None:
        return None
    return _rpc_error(id_, -32601, f"Method not found: {method}")


def _read_ndjson(raw: str) -> dict | None:
    raw = raw.strip()
    if not raw:
        return None
    return json.loads(raw)


def read_message(buf: bytes, leftover: bytes) -> tuple[dict | None, bytes, bool]:
    """Parse one message. Returns (msg, leftover, eof)."""
    data = leftover + buf
    if b"{" in data[:1] or (data.lstrip().startswith(b"{")):
        nl = data.find(b"\n")
        if nl < 0:
            return None, data, False
        line = data[:nl].decode("utf-8-sig", errors="replace").strip()
        rest = data[nl + 1 :]
        if not line:
            return None, rest, False
        return json.loads(line), rest, False
    header_end = data.find(b"\r\n\r\n")
    if header_end < 0:
        return None, data, False
    headers = data[:header_end].decode("ascii", errors="replace")
    length = 0
    for line in headers.split("\r\n"):
        if line.lower().startswith("content-length:"):
            length = int(line.split(":", 1)[1].strip())
    start = header_end + 4
    if len(data) < start + length:
        return None, data, False
    body = data[start : start + length].decode("utf-8", errors="replace")
    rest = data[start + length :]
    return json.loads(body), rest, False


def encode_message(msg: dict) -> bytes:
    body = json.dumps(msg, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def serve(stdin=None, stdout=None) -> int:
    inf = stdin or sys.stdin.buffer
    outf = stdout or sys.stdout.buffer
    leftover = b""
    while True:
        chunk = inf.read(4096)
        if not chunk:
            if leftover.strip():
                try:
                    msg = json.loads(leftover.decode("utf-8-sig", errors="replace").strip())
                    reply = handle(msg)
                    if reply is not None:
                        outf.write(encode_message(reply))
                        outf.flush()
                except Exception:
                    err = _rpc_error(None, -32700, "Parse error")
                    outf.write(encode_message(err))
                    outf.flush()
            break
        leftover += chunk
        while True:
            try:
                msg, leftover, _ = read_message(b"", leftover)
            except json.JSONDecodeError:
                err = _rpc_error(None, -32700, "Parse error")
                outf.write(encode_message(err))
                outf.flush()
                leftover = b""
                break
            if msg is None:
                break
            reply = handle(msg)
            if reply is not None:
                outf.write(encode_message(reply))
                outf.flush()
    return 0


def main() -> int:
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
