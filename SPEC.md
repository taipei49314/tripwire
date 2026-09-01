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

### M1 — 提交閘與收據閘

PreToolUse 攔 `git commit` / `git push`（含已 commit 範圍掃描）；walkaround 收據接 Stop 閘
（宣稱 done 需有入場收據）。判準屆時另立並凍結。

### M2 — MCP server

stdio MCP：`trust.score`（trust-meter）、`ledger.preregister` / `ledger.score`（nullbench）、
`receipt.verify`（walkaround）、`repo.investigate`（unasked / RepoPassport）。判準屆時另立。

### M3 — skills

`/preregister`（T 系列預註冊劇本）、`/adversarial-verify`、判決書格式。判準屆時另立。

## 4. 明確不做

- 不修改、不 fork、不 patch 任何裁判 repo 的偵測邏輯
- 不做 LLM 裁判、不連網裁決
- 不宣稱本地 hook 是完整 enforcement（required check 才是，見 §0）
- 不在 M0 摻入 M1+ 的範圍

## 5. 家族地圖（資產 → 層）

| 裁判 repo | 進入層 | 里程碑 |
| --- | --- | --- |
| greenwash | hooks | **M0** |
| walkaround | hooks | M1 |
| phaseledger | hooks | M1 |
| trust-meter | MCP | M2 |
| nullbench | MCP | M2 |
| unasked / RepoPassport | MCP | M2 |
| charterlock | 信任模型（§0）＋ M1 收據語義 | — |
| smallestlie | M2 之後評估（對抗性探針工具） | — |
| T 系列方法論（cell-shift T2–T6 實踐） | skills | M3 |
