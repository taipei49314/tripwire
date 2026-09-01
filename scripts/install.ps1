# tripwire installer (M0): vendor the pinned judge and self-check.
# Judges are pinned by git tag and never patched (SPEC section 2).

$ErrorActionPreference = "Stop"

$GreenwashRepo = "https://github.com/taipei49314/greenwash.git"
$GreenwashTag = "v0.1.47"

$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root "vendor"
$Target = Join-Path $Vendor "greenwash"

if (Test-Path $Target) {
    Write-Host "vendor/greenwash already present - removing for a clean pin."
    Remove-Item -Recurse -Force $Target
}
New-Item -ItemType Directory -Force $Vendor | Out-Null

# git chats on stderr (annotated-tag + shallow warnings); only the exit code
# decides. Stringify the stream so EAP=Stop does not mistake chatter for failure.
& git clone --quiet --depth 1 --branch $GreenwashTag $GreenwashRepo $Target 2>&1 |
    ForEach-Object { "$_" } | Out-Null
if ($LASTEXITCODE -ne 0) { throw "clone of greenwash@$GreenwashTag failed" }

$env:PYTHONPATH = (Join-Path $Target "src")
$version = python -m greenwash --version
if ($LASTEXITCODE -ne 0) { throw "greenwash self-check failed" }
Write-Host "vendored judge: $version (pin $GreenwashTag)"

$hook = Join-Path $Root "hooks\tripwire_stop.py"
Write-Host ""
Write-Host "Stop-hook snippet for a target repo's .claude/settings.json:"
Write-Host "----------------------------------------------------------------"
$snippet = @{
    hooks = @{
        Stop = @(
            @{ hooks = @(
                @{ type = "command"; command = "python `"$hook`"" }
            ) }
        )
    }
} | ConvertTo-Json -Depth 6
Write-Host $snippet
Write-Host "----------------------------------------------------------------"
Write-Host "done."
