# mcp (M2)

Query plane. **Not enforcement.** Hooks must not call this server.

```powershell
python mcp/tripwire_mcp.py
```

stdio JSON-RPC 2.0, Content-Length framing. Frozen tools (SPEC §3 M2):

| Tool | Judge |
| --- | --- |
| `trust.score` | trust-meter @ v0.2.1 |
| `ledger.preregister` | nullbench @ v0.8.2 |
| `ledger.score` | nullbench @ v0.8.2 |
| `receipt.verify` | walkaround @ v0.4.1 |
| `repo.investigate` | unasked @ v0.4.0 (`doctor`) |

Missing vendor → `isError` fail-closed. RepoPassport is not invoked this slice.
