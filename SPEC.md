# tripwire — 創始規格

**一句話：** 把 Nelson 的防 agent 技術群（greenwash、walkaround、charterlock、trust-meter、
phaseledger、nullbench、unasked、RepoPassport、smallestlie）熔成一個可以插進任何 agent host
的三層產品：**hooks 執法、MCP 查詢、skills 方法論**。

**預註冊聲明：** 本規格在任何里程碑實作之前提交（以本檔首次出現的 commit 為證）。
各里程碑的驗收判準自此凍結，開跑後不得改。

## 0. 北極星與信任模型

**考生不能自己出題、自己改考卷**（charterlock 原則）。因此：

- 「防」只能活在 agent 信任域**外面**——由 harness 強制執行的 hooks，agent 繞不過。
- 給 agent 自己調用的檢查（MCP tools）一律視為**便利**，不是 enforcement。
- 裁判必須決定性、零 LLM、可重播——裁判本身沒有 prompt-injection 面。
- 誠實警語（引 greenwash 自家文件）：本地 hook 是 author-side 便利，會被 `--no-verify`
  跳過；真正的 merge enforcement 是 required status check。tripwire 不假裝解決這一點。

## 1. 三層架構

| 層 | 機制 | 內容 | 信任性質 |
| --- | --- | --- | --- |
| 執法 | Claude Code hooks（Stop / PreToolUse） | greenwash 停手閘、walkaround 收據閘、phaseledger 關卡 | harness 強制，agent 繞不過 |
| 查詢 | MCP server（stdio） | trust-meter 評分、nullbench 預註冊帳本、收據查驗、unasked / RepoPassport 調查 | 便利與可觀測，非 enforcement |
| 方法論 | skills | 預註冊協定（T 系列）、對抗性驗證劇本、判決書格式 | 教誠實的 agent 做事 |

## 2. 裁判邊界（凍結的紀律）

1. **tripwire 永不擁有偵測邏輯。** 裁判留在各自的 repo，tripwire 以 **git tag 釘版** vendoring；
   升級裁判＝改一個 pin 並記錄，永不 fork、永不 patch 裁判源碼。
2. **裁判發現的問題不准在 tripwire 層修飾。** 判決原文透傳給 agent／使用者。
3. 已知事實：greenwash 發行版 `.pyz` 的 block 判決會 exit 0（其 FAILURES.md 自載）。
   因此 tripwire **只從原始碼 tag 安裝**，不用 pyz。

## 3. 里程碑與凍結判準

### M0 — greenwash 停手閘（本輪）

範圍：`hooks/tripwire_stop.py` ＋ `scripts/install.ps1`（vendor greenwash @ **v0.1.47**）＋
stdlib 測試＋自家 dogfood（tripwire repo 自帶 `.claude/settings.json` 掛鉤）。
檢查範圍＝HEAD..工作樹（greenwash `check` 預設）；已 commit 的竄改屬 M1。

驗收（全部成立才標 M0 done）：

| # | 判準 |
| --- | --- |
| A1 | `scripts/install.ps1` 在乾淨 checkout 完成 vendoring 並自檢（`--version` 印出 0.1.47、exit 0） |
| A2 | 弱化斷言且無實質產品變更的工作樹 → hook stdout 為 `{"decision":"block","reason":...}`（reason 含規則名），exit 0 |
| A3 | 乾淨樹或誠實變更 → hook stdout `{}`，exit 0 |
| A4 | stdin 帶 `stop_hook_active: true` → 直接放行 `{}`（防無限迴圈） |
| A5 | 裁判崩潰或逾時 → **fail-closed**：block 且 reason 註明 engine error；有測試覆蓋 |
| A6 | 非 git 目錄 → 放行 `{}`（hook 不該綁架無關工作） |
| A7 | 上述行為全部由 `python -m unittest` 鎖住，測試不碰網路 |

**M0 修訂紀錄（2026-09-01，狗糧第一天）**：實裝到 cell-shift 後第一次實彈即發現
wrapper 的 fail-open 暗道——PowerShell 管線在 stdin 前置 UTF-8 BOM → `json.load` 失敗 →
舊版退回 `os.getcwd()`（非 git 目錄）→ A6 靜默放行。裁判（greenwash）全程判決正確，
洞在 tripwire 包裝層的錯誤處理哲學：**payload 壞掉不准退回猜測，一律 fail-closed**。
修正並「新增」兩條鎖（不弱化任何原判準）：A8＝帶 BOM 的有效 payload 照常把關；
A9＝非 JSON 的 stdin → fail-closed block。生產路徑（Claude Code 的乾淨 stdin JSON）
自始未受影響；此洞只在手動／管線呼叫時可達。

### M1 — 提交閘與收據閘

兩刀。Stop 是「宣稱 done」；PreToolUse 是「把已發生的東西送進歷史」。
M0 只看工作樹，已 commit 的洗分屬這一層。

**M1-R、M1-C 已凍結並落地。本輪凍結並實作 M1-P（phaseledger 關卡接 Stop）。**
三刀齊了才算 M1 done。

#### M1-R — walkaround 收據接 Stop（本輪）

範圍：既有 `hooks/tripwire_stop.py` 在 greenwash 放行之後加一道入場收據閘；
`scripts/install.ps1` vendor walkaround @ **v0.4.1**（git tag，不 patch）；
stdlib 測試。裁判邊界不變：tripwire 不讀 walkaround 的規則，只讀
`walkaround hook` 的 exit 與原文。

Stop 對 harness 就是 done-claim。沒有 `ADMITTED` 收據＝沒進場。
greenwash 先跑：測試被洗時，即使收據是 `ADMITTED` 也擋（兩閘獨立）。
walkaround 不重做 freshness；過期收據是它自己的威脅模型（其 THREATMODEL
row 未宣稱 freshness），本輪不在 wrapper 補。

驗收（全部成立才標 M1-R done）。M0 A1–A9 **不得弱化**：A3 的乾淨樹在
setUp 植入一張 `ADMITTED` 收據後仍放行，這是組合而非改寫 A3。

| # | 判準 |
| --- | --- |
| R1 | `scripts/install.ps1` vendor walkaround @ v0.4.1，自檢 `python -m walkaround version` 印出 `0.4.1` |
| R2 | git 工作樹、greenwash 放行、**沒有** `.walkaround/receipt.json` → hook stdout `{"decision":"block",...}`，reason 含 `BYPASSED` 或 `no receipt`，exit 0 |
| R3 | 同上，但存著可 `verify` 的 `ADMITTED` 收據 → stdout `{}`，exit 0 |
| R4 | 存著 `REFUSED` 或 `INCOMPLETE` 收據 → block，reason 含 walkaround 的 verdict／code 原文 |
| R5 | 弱化斷言 **加上** `ADMITTED` 收據 → 仍 block，reason 走 greenwash（R 閘不得蓋掉 M0） |
| R6 | vendored walkaround 缺失、崩潰或逾時 → fail-closed block，reason 註明 engine error |
| R7 | `stop_hook_active: true` 仍短接到 `{}`（兩閘共用 M0 A4） |
| R8 | 非 git 目錄仍放行 `{}`（M0 A6） |
| R9 | 上述由 `python -m unittest` 鎖住，測試不碰網路 |

**預註冊：** 本表隨落地 commit 凍結。開跑後不得改判準來遷就實作。

#### M1-C — PreToolUse 提交閘（本輪）

範圍：`hooks/tripwire_pretooluse.py` ＋ dogfood `.claude/settings.json` 掛
`PreToolUse` / matcher `Bash`。裁判仍是 vendored greenwash @ **v0.1.47**，
不 patch。tripwire 只決定「這次呼叫要不要跑、跑哪一段範圍」，判決原文透傳。

為什麼 Stop 不夠：M0 看 HEAD..工作樹。agent 先把洗分 **commit 進歷史**，
工作樹變乾淨，Stop 放行；再 `git push`。M1-C 在工具執行前攔 `git commit`
與 `git push`。

觸發（命令字串、大小寫不敏感）：把 `&&` / `||` / `;` / 換行 / 單根 `|` 切開
之後，若某段的 git 子命令是 `commit` 或 `push`（可帶 `git -C`、`-c`、
`--git-dir`、`--work-tree`、前綴環境變數、`git.exe`）。`git commit-tree`、
`git commit-graph`、`git push-to-checkout` 不觸發。字串裡的註解與引號內
文字不做完整 shell 解析——殘差寫在下面。

範圍：

| 子命令 | greenwash 範圍 |
| --- | --- |
| `commit` | 預設 HEAD..工作樹（PreToolUse 在 commit 之前，洗分還在樹上） |
| `push` | 尚未在任何 remote-tracking ref 上的 local commit（`git rev-list HEAD --not --remotes`）。最舊一筆有 parent → `oldest^..HEAD`；最舊是根且後面還有 commit → `oldest..HEAD`（不含根）。只有根 commit 未推送：放行，依賴 commit 當下的工作樹閘 |
| 兩者都有（`git commit && git push`） | 兩段都跑，任一 block 則 deny |

PreToolUse 協議：stdout JSON `hookSpecificOutput.permissionDecision = deny`，
exit 0（不是 Stop 的 `decision: block`）。非 commit/push 的 Bash 呼叫不
作決定（stdout `{}`）。

驗收（全部成立才標 M1-C done）。M0 / M1-R **不得弱化**。

| # | 判準 |
| --- | --- |
| C1 | dogfood settings 掛 PreToolUse matcher `Bash` → `hooks/tripwire_pretooluse.py` |
| C2 | Bash 命令不是 git commit/push → stdout `{}`，exit 0 |
| C3 | `git commit`（或 `git add && git commit`）且工作樹弱化斷言、無產品變更 → deny，reason 含規則名 |
| C4 | `git commit` 乾淨樹或誠實變更 → stdout `{}` |
| C5 | 洗分**已經 commit**、工作樹乾淨、再 `git push` → deny，reason 含規則名（這是 M0 的洞） |
| C6 | `git push` 且未推送範圍乾淨 → stdout `{}` |
| C7 | `git commit-tree` / `git commit-graph` 不觸發閘 |
| C8 | 惡形 payload → deny，fail-closed |
| C9 | vendored greenwash 缺失 → deny，fail-closed |
| C10 | 非 git 目錄 → stdout `{}` |
| C11 | 上述由 `python -m unittest` 鎖住，測試不碰網路 |

**殘差（接受，不在本輪補）：** 任意 refspec（`git push other HEAD:foo`）、
`--all` / `--tags`、根 commit 且從未設 remote 的 push、引號內偽裝
`git commit` 字樣。真正的 merge enforcement 仍是 required check（§0）。

**預註冊：** 本表隨落地 commit 凍結。開跑後不得改判準來遷就實作。

#### M1-P — phaseledger 關卡接 Stop（本輪）

範圍：既有 `hooks/tripwire_stop.py` 在 walkaround 放行之後加一道 phase 關卡；
`scripts/install.ps1` vendor phaseledger @ **v0.6.0**（git tag，不 patch）。
裁判邊界不變：tripwire 不讀 ledger.json 欄位、不重做 measurer，只呼叫
`phaseledger verify` 與 `phaseledger status`，原文透傳。

為什麼收據不夠：walkaround `ADMITTED` 只表示進了場。phaseledger 的規則是
claim → measure → advance；空 ledger 的 `verify` 是 PASS（沒有進階狀態可
對不上）。Stop 是 done-claim，空關卡或跳關不能放行。

順序固定：greenwash → walkaround → phaseledger。前一閘 block 則不到這一閘。

帳本路徑凍結為工作樹 `.phaseledger/`（與 `.walkaround/` 同形）。

| 步驟 | 行為 |
| --- | --- |
| 沒有 `.phaseledger/ledger.json` | block，reason 含 `NO_LEDGER` |
| `phaseledger verify --ledger .phaseledger` 非 0 | block，reason 含 verify 原文（`VERIFY:`） |
| verify 為 0，但 `status` 原文沒有 ` ADVANCED \|` | block，reason 含 `NO_PHASE_ADVANCED`（空 init 的洞） |
| 至少一相 ADVANCED 且 verify PASS | 放行 `{}` |

跳關（後相 advanced、前相不是）由 **phaseledger verify** 自己拒絕
（`advanced while prior phase … is not advanced`）。tripwire 不另寫順序邏輯。

驗收（全部成立才標 M1-P done）。M0 / M1-R / M1-C **不得弱化**：A3 的放行
setUp 加種一相 `plan` ADVANCED，這是組合而非改寫 A3。

| # | 判準 |
| --- | --- |
| P1 | `scripts/install.ps1` vendor phaseledger @ v0.6.0，自檢 `--version` 含 `0.6.0` |
| P2 | walkaround `ADMITTED`、greenwash 放行、**沒有** `.phaseledger/ledger.json` → block，reason 含 `NO_LEDGER` |
| P3 | ledger `verify` FAIL（缺 capture / 壞 JSON / 跳關）→ block，reason 含 `VERIFY` |
| P4 | `phaseledger init` 空帳（verify PASS、無 ADVANCED）→ block，reason 含 `NO_PHASE_ADVANCED` |
| P5 | `plan` 已 ADVANCED、verify PASS、walkaround ADMITTED、乾淨樹 → stdout `{}` |
| P6 | vendored phaseledger 缺失、崩潰或逾時 → fail-closed block |
| P7 | 弱化斷言加上健康 phase ledger 仍走 greenwash block（P 閘不得蓋掉 M0） |
| P8 | `stop_hook_active` / 非 git 仍短接（M0 A4 / A6） |
| P9 | 上述由 `python -m unittest` 鎖住，測試不碰網路 |

**殘差：** 不在 Stop 檢查 Write/Edit 是否發生在 plan 之前（那是 agent 工作方式，
ledger 只在 claim/advance 時拒絕跳關）。觀察檔由作者寫入；tripwire 不代造
measure。真正的 merge enforcement 仍是 required check（§0）。

**預註冊：** 本表隨本輪 commit 凍結。開跑後不得改判準來遷就實作。

### M2 — MCP 查詢面（本輪）

**不是執法。** MCP 給 agent 自己調；hooks 不准改去呼叫 MCP（§0、§1）。
範圍：`mcp/tripwire_mcp.py` stdio JSON-RPC 2.0（Content-Length 框，兼讀 NDJSON）。
裁判仍 pin、不 patch；缺 vendor → `isError: true`，fail-closed。tripwire 不解析、
不修飾判決原文。

凍結工具名（`tools/list` 必須恰好這五個，順序穩定）：

| Tool | 裁判 / pin | 呼叫 |
| --- | --- | --- |
| `trust.score` | trust-meter @ **v0.2.1** | `python -m trust_meter.cli --json --no-config <target>` |
| `ledger.preregister` | nullbench @ **v0.8.2** | `python -m nullbench freeze --study <study> --latest` |
| `ledger.score` | nullbench @ **v0.8.2** | `python -m nullbench settle --study <study>` |
| `receipt.verify` | walkaround @ **v0.4.1** | `python -m walkaround --root <root> verify` |
| `repo.investigate` | unasked @ **v0.4.0** | `python -m unasked doctor --workspace <workspace>` |

`repo.investigate` 本輪是 harness 健康檢查（`doctor`），不是一次完整
Explorer 調查。RepoPassport 本輪不呼叫（Go 執行檔，殘差）。

參數皆為字串路徑。缺參數 → `isError`。未知 tool 名 → `isError`。
惡形 JSON-RPC → JSON-RPC error（parse -32700 / invalid -32600）。

驗收（全部成立才標 M2 done）。M0 / M1 **不得弱化**。

| # | 判準 |
| --- | --- |
| M2-1 | `initialize` 回 `protocolVersion`、`serverInfo.name = tripwire`、`capabilities.tools` |
| M2-2 | `tools/list` 恰好五個名字，順序同上 |
| M2-3 | 未知 tool → `isError: true`，exit 路徑仍 0（JSON-RPC result，不是 process crash） |
| M2-4 | 缺 vendor → `isError: true`，reason 含 `Failing closed` |
| M2-5 | `receipt.verify` 對已有 ADMITTED 收據 → `isError` 假，text 含 `ADMITTED` |
| M2-6 | `receipt.verify` 無收據 → `isError` 真（walkaround hook/verify 非 0 原文） |
| M2-7 | MCP **沒有**掛進 Stop / PreToolUse |
| M2-8 | stdlib unittest，測試不碰網路 |

**殘差：** nullbench 依賴 typer/numpy，本輪測試不要求 live freeze/settle
（M2-4 鎖缺 vendor）。完整 `unasked investigate` 與 RepoPassport `verify`
不在本輪。MCP 被 `--no-verify` 或關掉 server 等於沒查詢，不是執法洞。

**預註冊：** 本表隨本輪 commit 凍結。

### M3 — skills 方法論（本輪）

**不是執法。** skills 教誠實的 agent 怎麼做；hooks 不准改去讀 SKILL.md。
範圍：`skills/<name>/SKILL.md` 三份，YAML `name` 與目錄名相同。

| Skill | 職責 |
| --- | --- |
| `preregister` | T 系列：先寫預測／claim，再跑裁判。禁止看完結果再改預測 |
| `adversarial-verify` | 對 M0/M1 閘做對照實驗（洗分、沒收據、空 ledger、跳關、先 commit 再 push） |
| `verdict-format` | 跨層判決詞彙：Stop `decision`、walkaround 四值、phaseledger 關卡碼、PreToolUse `permissionDecision`、MCP `isError` |

驗收（全部成立才標 M3 done）。M0 / M1 / M2 **不得弱化**。

| # | 判準 |
| --- | --- |
| S1 | 三份 `skills/{preregister,adversarial-verify,verdict-format}/SKILL.md` 存在，frontmatter `name:` 與目錄名相同 |
| S2 | `preregister` 含 `claim before measure` 與 `no backfill` |
| S3 | `adversarial-verify` 點名三道 Stop 閘：`greenwash`、`walkaround`、`phaseledger`，以及 M1-C `git push` |
| S4 | `verdict-format` 含 `ADMITTED`、`BYPASSED`、`NO_LEDGER`、`NO_PHASE_ADVANCED`、`permissionDecision`、`isError` |
| S5 | skills **沒有**掛進 Stop / PreToolUse |
| S6 | stdlib unittest，測試不碰網路 |

**殘差：** skill 不能阻止不誠實的 agent；那是 hooks 的工作。本輪不做 Claude 以外 host 的自動安裝。

**預註冊：** 本表隨本輪 commit 凍結。

## 4. 明確不做

- 不修改、不 fork、不 patch 任何裁判 repo 的偵測邏輯
- 不做 LLM 裁判、不連網裁決
- 不宣稱本地 hook 是完整 enforcement（required check 才是，見 §0）
- 不在 M0 摻入 M1+ 的範圍

## 5. 家族地圖（資產 → 層）

| 裁判 repo | 進入層 | 里程碑 |
| --- | --- | --- |
| greenwash | hooks | **M0** ＋ **M1-C（範圍掃描）** |
| walkaround | hooks | **M1-R** |
| phaseledger | hooks | **M1-P（本輪）** |
| trust-meter | MCP | **M2** |
| nullbench | MCP | **M2**（pin；live settle 殘差） |
| unasked | MCP | **M2**（doctor） |
| RepoPassport | MCP | M2 殘差（未呼叫） |
| charterlock | 信任模型（§0）＋ M1 收據語義 | — |
| smallestlie | M2 之後評估（對抗性探針工具） | — |
| T 系列方法論 | skills | **M3** |
