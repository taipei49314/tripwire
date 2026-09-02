# tripwire installer (M0 + M1 + M2): vendor pinned judges and self-check.
# Judges are pinned by git tag and never patched (SPEC section 2).

$ErrorActionPreference = "Stop"

# GitHub renamed greenwash -> checkwash. The v0.1.47 tag still peels on that
# history and is the frozen M0/M4 judge. Do not retarget this pin to current
# checkwash (different engine; checkwash release is frozen).
$GreenwashRepo = "https://github.com/taipei49314/greenwash.git"
$GreenwashTag = "v0.1.47"
$WalkaroundRepo = "taipei49314/walkaround"
$WalkaroundTag = "v0.4.1"
$PhaseledgerRepo = "https://github.com/taipei49314/phaseledger.git"
$PhaseledgerTag = "v0.6.0"
$TrustMeterRepo = "taipei49314/trust-meter"
$TrustMeterTag = "v0.2.1"
$UnaskedRepo = "taipei49314/unasked"
$UnaskedTag = "v0.4.0"
$NullbenchRepo = "https://github.com/taipei49314/nullbench.git"
$NullbenchTag = "v0.8.2"
$CharterlockRepo = "https://github.com/taipei49314/charterlock.git"
$CharterlockTag = "v0.1.0"
$RepoPassRepo = "https://github.com/taipei49314/RepoPassport.git"
$RepoPassTag = "v0.1.0-alpha.33"

$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root "vendor"
$Target = Join-Path $Vendor "greenwash"
$WalkaroundTarget = Join-Path $Vendor "walkaround"
$PhaseledgerTarget = Join-Path $Vendor "phaseledger"
$TrustMeterTarget = Join-Path $Vendor "trust-meter"
$UnaskedTarget = Join-Path $Vendor "unasked"
$NullbenchTarget = Join-Path $Vendor "nullbench"
$CharterlockTarget = Join-Path $Vendor "charterlock"
$RepoPassTarget = Join-Path $Vendor "RepoPassport"

if (Test-Path $Target) {
    Write-Host "vendor/greenwash already present - removing for a clean pin."
    Remove-Item -Recurse -Force $Target
}
New-Item -ItemType Directory -Force $Vendor | Out-Null

# git writes annotated-tag peel warnings to stderr. EAP=Stop treats native
# stderr as terminating; cmd /c lets only the exit code decide.
cmd /c "git clone --quiet --depth 1 --branch $GreenwashTag `"$GreenwashRepo`" `"$Target`""
if ($LASTEXITCODE -ne 0) { throw "clone of greenwash@$GreenwashTag failed" }

$env:PYTHONPATH = (Join-Path $Target "src")
$version = python -m greenwash --version
if ($LASTEXITCODE -ne 0) { throw "greenwash self-check failed" }
Write-Host "vendored judge: $version (pin $GreenwashTag)"

if (Test-Path $WalkaroundTarget) {
    Write-Host "vendor/walkaround already present - removing for a clean pin."
    Remove-Item -Recurse -Force $WalkaroundTarget
}
cmd /c "gh repo clone $WalkaroundRepo `"$WalkaroundTarget`" -- --quiet --depth 1 --branch $WalkaroundTag"
if ($LASTEXITCODE -ne 0) { throw "clone of walkaround@$WalkaroundTag failed" }

$env:PYTHONPATH = $WalkaroundTarget
$waVersion = python -m walkaround version
if ($LASTEXITCODE -ne 0) { throw "walkaround self-check failed" }
if ($waVersion.Trim() -ne "0.4.1") { throw "walkaround pin mismatch: got $waVersion want 0.4.1" }
Write-Host "vendored judge: walkaround $waVersion (pin $WalkaroundTag)"

if (Test-Path $PhaseledgerTarget) {
    Write-Host "vendor/phaseledger already present - removing for a clean pin."
    Remove-Item -Recurse -Force $PhaseledgerTarget
}
cmd /c "git clone --quiet --depth 1 --branch $PhaseledgerTag `"$PhaseledgerRepo`" `"$PhaseledgerTarget`""
if ($LASTEXITCODE -ne 0) { throw "clone of phaseledger@$PhaseledgerTag failed" }

$env:PYTHONPATH = $PhaseledgerTarget
$plVersion = python -m phaseledger --version
if ($LASTEXITCODE -ne 0) { throw "phaseledger self-check failed" }
if ($plVersion -notmatch "0\.6\.0") { throw "phaseledger pin mismatch: got $plVersion want 0.6.0" }
Write-Host "vendored judge: $plVersion (pin $PhaseledgerTag)"

if (Test-Path $TrustMeterTarget) {
    Write-Host "vendor/trust-meter already present - removing for a clean pin."
    Remove-Item -Recurse -Force $TrustMeterTarget
}
cmd /c "gh repo clone $TrustMeterRepo `"$TrustMeterTarget`" -- --quiet --depth 1 --branch $TrustMeterTag"
if ($LASTEXITCODE -ne 0) { throw "clone of trust-meter@$TrustMeterTag failed" }
$env:PYTHONPATH = Join-Path $TrustMeterTarget "src"
$tmVersion = python -m trust_meter.cli --version
if ($LASTEXITCODE -ne 0) { throw "trust-meter self-check failed" }
Write-Host "vendored judge: $tmVersion (pin $TrustMeterTag)"

if (Test-Path $UnaskedTarget) {
    Write-Host "vendor/unasked already present - removing for a clean pin."
    Remove-Item -Recurse -Force $UnaskedTarget
}
cmd /c "gh repo clone $UnaskedRepo `"$UnaskedTarget`" -- --quiet --depth 1 --branch $UnaskedTag"
if ($LASTEXITCODE -ne 0) { throw "clone of unasked@$UnaskedTag failed" }
$env:PYTHONPATH = Join-Path $UnaskedTarget "src"
$unVersion = python -m unasked --version
if ($LASTEXITCODE -ne 0) { throw "unasked self-check failed" }
Write-Host "vendored judge: $unVersion (pin $UnaskedTag)"

if (Test-Path $NullbenchTarget) {
    Write-Host "vendor/nullbench already present - removing for a clean pin."
    Remove-Item -Recurse -Force $NullbenchTarget
}
cmd /c "git clone --quiet --depth 1 --branch $NullbenchTag `"$NullbenchRepo`" `"$NullbenchTarget`""
if ($LASTEXITCODE -ne 0) { throw "clone of nullbench@$NullbenchTag failed" }
Write-Host "vendored judge: nullbench source pin $NullbenchTag"
python -m pip install -e $NullbenchTarget -q
if ($LASTEXITCODE -ne 0) { throw "nullbench pip install failed" }
$nbVersion = python -m nullbench version
if ($LASTEXITCODE -ne 0) { throw "nullbench self-check failed" }
Write-Host "vendored judge: $nbVersion (pin $NullbenchTag)"

if (Test-Path $CharterlockTarget) {
    Write-Host "vendor/charterlock already present - removing for a clean pin."
    Remove-Item -Recurse -Force $CharterlockTarget
}
cmd /c "git clone --quiet --depth 1 --branch $CharterlockTag `"$CharterlockRepo`" `"$CharterlockTarget`""
if ($LASTEXITCODE -ne 0) { throw "clone of charterlock@$CharterlockTag failed" }
$env:PYTHONPATH = $CharterlockTarget
$clVersion = python -c "import charterlock; print(charterlock.__version__)" 2>$null
if (-not $clVersion) { $clVersion = "charterlock (no __version__)" }
Write-Host "vendored judge: $clVersion (pin $CharterlockTag)"

if (Test-Path $RepoPassTarget) {
    Write-Host "vendor/RepoPassport already present - removing for a clean pin."
    Remove-Item -Recurse -Force $RepoPassTarget
}
cmd /c "git clone --quiet --depth 1 --branch $RepoPassTag `"$RepoPassRepo`" `"$RepoPassTarget`""
if ($LASTEXITCODE -ne 0) { throw "clone of RepoPassport@$RepoPassTag failed" }
Write-Host "vendored judge: RepoPassport source pin $RepoPassTag (go run ./cmd/repopass)"

$stopHook = Join-Path $Root "hooks\tripwire_stop.py"
$preHook = Join-Path $Root "hooks\tripwire_pretooluse.py"
Write-Host ""
Write-Host "Hook snippet for a target repo's .claude/settings.json:"
Write-Host "----------------------------------------------------------------"
$snippet = @{
    hooks = @{
        Stop = @(
            @{ hooks = @(
                @{ type = "command"; command = "python `"$stopHook`"" }
            ) }
        )
        PreToolUse = @(
            @{
                matcher = "Write|Edit|Bash"
                hooks = @(
                    @{ type = "command"; command = "python `"$preHook`"" }
                )
            }
        )
    }
} | ConvertTo-Json -Depth 6
Write-Host $snippet
Write-Host "----------------------------------------------------------------"
Write-Host "done."
