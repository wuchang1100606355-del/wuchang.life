param(
    [string]$OutputRoot = "",
    [int]$TimeoutSec = 20,
    [switch]$RepairUserPath,
    [string]$SyncEvidenceRoot = ""
)

$ErrorActionPreference = "Continue"

function New-SafeDirectory {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Convert-ToSafeString {
    param($Value)
    if ($null -eq $Value) {
        return ""
    }
    return (($Value | Out-String).Trim())
}

function Copy-EvidenceTree {
    param([string]$SourceRoot, [string]$TargetRoot)
    if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
        return @{
            attempted = $false
            ok = $false
            reason = "sync target not requested"
        }
    }
    try {
        New-SafeDirectory $TargetRoot
        Copy-Item -Path (Join-Path $SourceRoot "*") -Destination $TargetRoot -Recurse -Force -ErrorAction Stop
        return @{
            attempted = $true
            ok = $true
            source = $SourceRoot
            target = $TargetRoot
        }
    } catch {
        return @{
            attempted = $true
            ok = $false
            source = $SourceRoot
            target = $TargetRoot
            error = $_.Exception.Message
        }
    }
}

function Get-LatestRepairReport {
    param([string]$Root)
    $dir = Get-ChildItem -LiteralPath $Root -Directory -Filter "windows_gpt_codex_repair_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($null -eq $dir) {
        return @{
            found = $false
            error = "no windows_gpt_codex_repair_* directory found"
        }
    }
    $reportPath = Join-Path $dir.FullName "WINDOWS_GPT_CODEX_REPAIR_REPORT.json"
    return @{
        found = (Test-Path -LiteralPath $reportPath)
        directory = $dir.FullName
        report_path = $reportPath
    }
}

function Read-JsonFileSafe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path)) {
        return @{
            ok = $false
            path = $Path
            error = "json file not found"
            data = $null
        }
    }
    try {
        $data = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        return @{
            ok = $true
            path = $Path
            error = ""
            data = $data
        }
    } catch {
        return @{
            ok = $false
            path = $Path
            error = $_.Exception.Message
            data = $null
        }
    }
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $env:USERPROFILE "Taiji_Hub\evidence"
}
New-SafeDirectory $OutputRoot

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repairScript = Join-Path $scriptRoot "windows_gpt_codex_repair.ps1"
$triageScript = Join-Path $scriptRoot "triage_windows_gpt_codex_report.py"
$readinessScript = Join-Path $scriptRoot "verify_windows_gpt_codex_readiness.ps1"

$launcherTimestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$launcherDir = Join-Path $OutputRoot "windows_gpt_codex_full_repair_launcher_$launcherTimestamp"
New-SafeDirectory $launcherDir

$repairInvocation = @{
    attempted = $false
    ok = $false
    output = ""
    error = ""
    report_path = ""
}

if (Test-Path -LiteralPath $repairScript) {
    $repairInvocation.attempted = $true
    try {
        $repairArgs = @("-OutputRoot", $OutputRoot, "-TimeoutSec", "$TimeoutSec", "-ApplySafeFixes")
        if ($RepairUserPath) {
            $repairArgs += "-RepairUserPath"
        }
        $repairOutput = & $repairScript @repairArgs 2>&1
        $repairInvocation.output = Convert-ToSafeString $repairOutput
        $reportLine = @($repairOutput | Where-Object { "$_" -like "REPORT=*" } | Select-Object -First 1)
        if ($reportLine.Count -gt 0) {
            $repairInvocation.report_path = ("$($reportLine[0])" -replace "^REPORT=", "")
        }
        $repairInvocation.ok = $true
    } catch {
        $repairInvocation.error = $_.Exception.Message
    }
} else {
    $repairInvocation.error = "repair script not found: $repairScript"
}

if ([string]::IsNullOrWhiteSpace($repairInvocation.report_path) -or -not (Test-Path -LiteralPath $repairInvocation.report_path)) {
    $latest = Get-LatestRepairReport $OutputRoot
    if ($latest.found) {
        $repairInvocation.report_path = $latest.report_path
    }
}

$triageInvocation = @{
    attempted = $false
    ok = $false
    output = ""
    error = ""
    python_command = ""
}

if (-not (Test-Path -LiteralPath $repairInvocation.report_path)) {
    $triageInvocation.error = "repair report not found; triage not attempted"
} elseif (-not (Test-Path -LiteralPath $triageScript)) {
    $triageInvocation.error = "triage script not found: $triageScript"
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        $python = Get-Command py -ErrorAction SilentlyContinue
    }
    if ($null -eq $python) {
        $triageInvocation.error = "python or py command not found"
        $notePath = Join-Path (Split-Path -Parent $repairInvocation.report_path) "PYTHON_TRIAGE_NOT_RUN.txt"
        @(
            "schema=TAIJI_WINDOWS_GPT_CODEX_TRIAGE_NOT_RUN_V1",
            "generated_at_utc=$((Get-Date).ToUniversalTime().ToString("o"))",
            "reason=python_or_py_command_not_found",
            "repair_report=$($repairInvocation.report_path)",
            "side_effects.installs_packages=false"
        ) | Set-Content -Path $notePath -Encoding UTF8
    } else {
        try {
            $triageInvocation.attempted = $true
            $triageInvocation.python_command = Convert-ToSafeString $python.Source
            $triageOutput = & $python.Source $triageScript $repairInvocation.report_path --out-dir (Split-Path -Parent $repairInvocation.report_path) 2>&1
            $triageInvocation.output = Convert-ToSafeString $triageOutput
            $triageInvocation.ok = $true
        } catch {
            $triageInvocation.error = $_.Exception.Message
        }
    }
}

$readinessInvocation = @{
    attempted = $false
    ok = $false
    output = ""
    error = ""
    report_path = ""
}

if (Test-Path -LiteralPath $readinessScript) {
    $readinessInvocation.attempted = $true
    try {
        $readinessOutput = & $readinessScript -OutputRoot $OutputRoot -TimeoutSec $TimeoutSec 2>&1
        $readinessInvocation.output = Convert-ToSafeString $readinessOutput
        $readinessLine = @($readinessOutput | Where-Object { "$_" -like "READINESS_REPORT=*" } | Select-Object -First 1)
        if ($readinessLine.Count -gt 0) {
            $readinessInvocation.report_path = ("$($readinessLine[0])" -replace "^READINESS_REPORT=", "")
        }
        $readinessInvocation.ok = $true
    } catch {
        $readinessInvocation.error = $_.Exception.Message
    }
} else {
    $readinessInvocation.error = "readiness script not found: $readinessScript"
}

$repairReportRead = Read-JsonFileSafe $repairInvocation.report_path
$readinessReportRead = Read-JsonFileSafe $readinessInvocation.report_path

$repairState = @{
    report_read_ok = [bool]$repairReportRead.ok
    report_read_error = $repairReportRead.error
    changes_user_path = $false
    codex_initial_present = $null
    codex_post_repair_present = $null
    codex_post_repair_version_ok = $null
}
if ($repairReportRead.ok) {
    $repairData = $repairReportRead.data
    $repairState.changes_user_path = [bool]$repairData.side_effects.changes_user_path
    $repairState.codex_initial_present = [bool]$repairData.commands.codex.present
    if ($null -ne $repairData.post_repair_commands -and $null -ne $repairData.post_repair_commands.codex) {
        $repairState.codex_post_repair_present = [bool]$repairData.post_repair_commands.codex.present
    }
    if ($null -ne $repairData.post_repair_versions -and $null -ne $repairData.post_repair_versions.codex) {
        $repairState.codex_post_repair_version_ok = [bool]$repairData.post_repair_versions.codex.ok
    }
}

$readinessState = @{
    report_read_ok = [bool]$readinessReportRead.ok
    report_read_error = $readinessReportRead.error
    state = ""
    codex_present = $false
    codex_version_ok = $false
    openai_api_status = $null
    failures = @()
    warnings = @()
}
if ($readinessReportRead.ok) {
    $readinessData = $readinessReportRead.data
    $readinessState.state = Convert-ToSafeString $readinessData.state
    $readinessState.codex_present = [bool]$readinessData.codex.present
    $readinessState.codex_version_ok = [bool]$readinessData.codex.version.ok
    $readinessState.failures = @($readinessData.failures)
    $readinessState.warnings = @($readinessData.warnings)
    $apiEndpoint = @($readinessData.endpoints | Where-Object { $_.name -eq "openai_api" } | Select-Object -First 1)
    if ($apiEndpoint.Count -gt 0) {
        $readinessState.openai_api_status = $apiEndpoint[0].https_head.status_code
    }
}

$apiReady = ($readinessState.openai_api_status -eq 200 -or $readinessState.openai_api_status -eq 401)
$completionReady = (
    $readinessState.state -eq "PASS_WINDOWS_GPT_CODEX_READINESS" -and
    [bool]$readinessState.codex_present -and
    [bool]$readinessState.codex_version_ok -and
    [bool]$apiReady -and
    @($readinessState.failures).Count -eq 0
)
$launcherState = if ($completionReady) { "PASS_WINDOWS_GPT_CODEX_REPAIR_VERIFIED" } else { "HOLD_WINDOWS_GPT_CODEX_REPAIR_NOT_VERIFIED" }

$launcherReport = @{
    schema = "TAIJI_WINDOWS_GPT_CODEX_FULL_REPAIR_LAUNCHER_V1"
    state = $launcherState
    completion_ready = [bool]$completionReady
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    output_root = $OutputRoot
    repair_user_path_requested = [bool]$RepairUserPath
    side_effects = @{
        installs_packages = $false
        changes_network_settings = $false
        reads_secret_values = $false
        external_api_mutation = $false
        may_change_user_path = [bool]$RepairUserPath
        actual_changes_user_path = [bool]$repairState.changes_user_path
    }
    repair_invocation = $repairInvocation
    triage_invocation = $triageInvocation
    readiness_invocation = $readinessInvocation
    repair_state = $repairState
    readiness_state = $readinessState
}

$jsonPath = Join-Path $launcherDir "FULL_REPAIR_LAUNCH_REPORT.json"
$textPath = Join-Path $launcherDir "FULL_REPAIR_LAUNCH_SUMMARY.txt"
$sealPath = Join-Path $launcherDir "FULL_REPAIR_EVIDENCE_SEAL.txt"

$launcherReport | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

$summary = @(
    "TAIJI_WINDOWS_GPT_CODEX_FULL_REPAIR_LAUNCHER_V1",
    "generated_at_utc=$($launcherReport.generated_at_utc)",
    "repair_report=$($repairInvocation.report_path)",
    "repair_ok=$($repairInvocation.ok)",
    "triage_ok=$($triageInvocation.ok)",
    "triage_error=$($triageInvocation.error)",
    "readiness_ok=$($readinessInvocation.ok)",
    "readiness_report=$($readinessInvocation.report_path)",
    "readiness_error=$($readinessInvocation.error)",
    "actual_changes_user_path=$($repairState.changes_user_path)",
    "codex_initial_present=$($repairState.codex_initial_present)",
    "codex_post_repair_present=$($repairState.codex_post_repair_present)",
    "codex_post_repair_version_ok=$($repairState.codex_post_repair_version_ok)",
    "readiness_state=$($readinessState.state)",
    "readiness_codex_present=$($readinessState.codex_present)",
    "readiness_codex_version_ok=$($readinessState.codex_version_ok)",
    "readiness_openai_api_status=$($readinessState.openai_api_status)",
    "completion_ready=$completionReady",
    "launcher_report=$jsonPath"
)
$summary | Set-Content -Path $textPath -Encoding UTF8

$jsonHash = (Get-FileHash -Algorithm SHA256 -Path $jsonPath).Hash.ToLowerInvariant()
$textHash = (Get-FileHash -Algorithm SHA256 -Path $textPath).Hash.ToLowerInvariant()
$seal = @(
    "schema=TAIJI_WINDOWS_GPT_CODEX_FULL_REPAIR_SEAL_V1",
    "generated_at_utc=$((Get-Date).ToUniversalTime().ToString("o"))",
    "launcher_report=$jsonPath",
    "launcher_report_sha256=$jsonHash",
    "launcher_summary=$textPath",
    "launcher_summary_sha256=$textHash",
    "side_effects.installs_packages=false",
    "side_effects.changes_network_settings=false",
    "side_effects.reads_secret_values=false",
    "side_effects.external_api_mutation=false",
    "side_effects.may_change_user_path=$([bool]$RepairUserPath)",
    "side_effects.actual_changes_user_path=$([bool]$repairState.changes_user_path)",
    "completion_ready=$completionReady",
    "launcher_state=$launcherState",
    "readiness_state=$($readinessState.state)",
    "readiness_codex_present=$($readinessState.codex_present)",
    "readiness_codex_version_ok=$($readinessState.codex_version_ok)",
    "readiness_openai_api_status=$($readinessState.openai_api_status)"
)
$seal | Set-Content -Path $sealPath -Encoding UTF8

$syncInvocation = Copy-EvidenceTree $OutputRoot $SyncEvidenceRoot
if ($syncInvocation.attempted) {
    $syncReportPath = Join-Path $launcherDir "EVIDENCE_SYNC_REPORT.json"
    $syncInvocation | ConvertTo-Json -Depth 10 | Set-Content -Path $syncReportPath -Encoding UTF8
    try {
        Copy-Item -LiteralPath $syncReportPath -Destination (Join-Path $SyncEvidenceRoot "EVIDENCE_SYNC_REPORT.json") -Force -ErrorAction Stop
    } catch {
        $syncInvocation["sync_report_copy_error"] = $_.Exception.Message
        $syncInvocation | ConvertTo-Json -Depth 10 | Set-Content -Path $syncReportPath -Encoding UTF8
    }
}

Write-Output "STATE=$launcherState"
Write-Output "REPAIR_REPORT=$($repairInvocation.report_path)"
Write-Output "TRIAGE_OK=$($triageInvocation.ok)"
Write-Output "READINESS_REPORT=$($readinessInvocation.report_path)"
Write-Output "LAUNCHER_REPORT=$jsonPath"
Write-Output "LAUNCHER_SEAL=$sealPath"
if ($syncInvocation.attempted) {
    Write-Output "SYNC_OK=$($syncInvocation.ok)"
    Write-Output "SYNC_TARGET=$($syncInvocation.target)"
}

if ($completionReady) {
    exit 0
}
exit 1
