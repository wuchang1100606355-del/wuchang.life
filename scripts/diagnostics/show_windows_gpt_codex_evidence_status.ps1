param(
    [string]$SyncRoot = ""
)

$ErrorActionPreference = "Continue"

function Convert-ToSafeString {
    param($Value)
    if ($null -eq $Value) {
        return ""
    }
    return (($Value | Out-String).Trim())
}

function Get-LatestFile {
    param(
        [string]$Root,
        [string]$Filter
    )
    if (-not (Test-Path -LiteralPath $Root)) {
        return $null
    }
    return Get-ChildItem -LiteralPath $Root -Recurse -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Read-KeyValueFile {
    param([string]$Path)
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) {
        return $result
    }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -notmatch "=") {
            continue
        }
        $parts = $line.Split("=", 2)
        $result[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $result
}

if ([string]::IsNullOrWhiteSpace($SyncRoot)) {
    $SyncRoot = Join-Path (Get-Location) "evidence_from_windows_current"
}

Write-Output "TAIJI_WINDOWS_GPT_CODEX_EVIDENCE_STATUS_V1"
Write-Output "sync_root=$SyncRoot"

if (-not (Test-Path -LiteralPath $SyncRoot)) {
    Write-Output "STATE=HOLD_WINDOWS_EVIDENCE_SYNC_ROOT_MISSING"
    Write-Output "reason=evidence_from_windows_current_missing"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}

$readiness = Get-LatestFile -Root $SyncRoot -Filter "WINDOWS_GPT_CODEX_READINESS_REPORT.json"
$seal = Get-LatestFile -Root $SyncRoot -Filter "READINESS_EVIDENCE_SEAL.txt"
$repair = Get-LatestFile -Root $SyncRoot -Filter "WINDOWS_GPT_CODEX_REPAIR_REPORT.json"
$launch = Get-LatestFile -Root $SyncRoot -Filter "FULL_REPAIR_LAUNCH_REPORT.json"
$sync = Get-LatestFile -Root $SyncRoot -Filter "EVIDENCE_SYNC_REPORT.json"

Write-Output "readiness_report=$(if ($readiness) { $readiness.FullName } else { '' })"
Write-Output "readiness_seal=$(if ($seal) { $seal.FullName } else { '' })"
Write-Output "repair_report=$(if ($repair) { $repair.FullName } else { '' })"
Write-Output "launch_report=$(if ($launch) { $launch.FullName } else { '' })"
Write-Output "sync_report=$(if ($sync) { $sync.FullName } else { '' })"

if (-not $readiness) {
    Write-Output "STATE=HOLD_WINDOWS_READINESS_REPORT_MISSING"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}
if (-not $seal) {
    Write-Output "STATE=HOLD_WINDOWS_READINESS_SEAL_MISSING"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}

$readinessJson = $null
try {
    $readinessJson = Get-Content -LiteralPath $readiness.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Output "readiness_state=$($readinessJson.state)"
    Write-Output "codex_present=$($readinessJson.codex.present)"
    Write-Output "codex_version_ok=$($readinessJson.codex.version.ok)"
} catch {
    Write-Output "STATE=HOLD_WINDOWS_READINESS_PARSE_FAILED"
    Write-Output "readiness_parse_error=$(Convert-ToSafeString $_.Exception.Message)"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}

$sealValues = Read-KeyValueFile -Path $seal.FullName
$expectedReadinessHash = $sealValues["readiness_report_sha256"]
if ([string]::IsNullOrWhiteSpace($expectedReadinessHash)) {
    Write-Output "STATE=HOLD_WINDOWS_READINESS_SEAL_INCOMPLETE"
    Write-Output "reason=readiness_report_sha256_missing"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}

$actualReadinessHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $readiness.FullName).Hash.ToLowerInvariant()
Write-Output "readiness_report_sha256=$actualReadinessHash"
Write-Output "readiness_seal_expected_sha256=$expectedReadinessHash"

if ($actualReadinessHash -ne $expectedReadinessHash.ToLowerInvariant()) {
    Write-Output "STATE=HOLD_WINDOWS_READINESS_SEAL_MISMATCH"
    Write-Output "next_action=00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
    exit 1
}

if ($launch) {
    try {
        $launchJson = Get-Content -LiteralPath $launch.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        Write-Output "launch_state=$($launchJson.state)"
        Write-Output "launch_completion_ready=$($launchJson.completion_ready)"
    } catch {
        Write-Output "launch_parse_error=$(Convert-ToSafeString $_.Exception.Message)"
    }
}

if ($readinessJson.state -eq "PASS_WINDOWS_GPT_CODEX_READINESS") {
    Write-Output "STATE=READY_FOR_LINUX_COLLECTION"
    Write-Output "next_action=bash ./00_CHECK_CURRENT_STATUS.sh"
    exit 0
}

Write-Output "STATE=HOLD_WINDOWS_READINESS_NOT_PASS"
Write-Output "next_action=review readiness report or rerun 00_DOUBLE_CLICK_REPAIR_WINDOWS_GPT_CODEX.cmd"
exit 1
