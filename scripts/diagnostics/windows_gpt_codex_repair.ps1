param(
    [string]$OutputRoot = "",
    [int]$TimeoutSec = 20,
    [switch]$ApplySafeFixes,
    [switch]$RepairUserPath
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

function Get-CommandProbe {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $cmd) {
        return @{
            name = $Name
            present = $false
        }
    }
    return @{
        name = $Name
        present = $true
        command_type = Convert-ToSafeString $cmd.CommandType
        source = Convert-ToSafeString $cmd.Source
        path = Convert-ToSafeString $cmd.Path
        definition = Convert-ToSafeString $cmd.Definition
    }
}

function Invoke-CommandProbe {
    param([string]$FilePath, [string[]]$Arguments)
    $job = $null
    try {
        $job = Start-Job -ScriptBlock {
            param([string]$InnerFilePath, [string[]]$InnerArguments)
            & $InnerFilePath @InnerArguments 2>&1
        } -ArgumentList $FilePath, $Arguments
        if (-not (Wait-Job -Job $job -Timeout $TimeoutSec)) {
            Stop-Job -Job $job -ErrorAction SilentlyContinue | Out-Null
            return @{
                ok = $false
                timed_out = $true
                command = "$FilePath $($Arguments -join ' ')"
                error = "command timed out after $TimeoutSec seconds"
            }
        }
        $output = Receive-Job -Job $job 2>&1
        return @{
            ok = $true
            timed_out = $false
            command = "$FilePath $($Arguments -join ' ')"
            output = Convert-ToSafeString $output
        }
    } catch {
        return @{
            ok = $false
            timed_out = $false
            command = "$FilePath $($Arguments -join ' ')"
            error = $_.Exception.Message
        }
    } finally {
        if ($null -ne $job) {
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue | Out-Null
        }
    }
}

function Get-EnvPresence {
    param([string]$Name, [bool]$SecretLike)
    if ($SecretLike) {
        $processPresent = Test-Path -LiteralPath "Env:$Name"
        $userPresent = $false
        $machinePresent = $false
        try {
            $userKey = Get-Item -LiteralPath "HKCU:\Environment" -ErrorAction Stop
            $userPresent = @($userKey.GetValueNames()) -contains $Name
        } catch {
            $userPresent = $false
        }
        try {
            $machineKey = Get-Item -LiteralPath "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" -ErrorAction Stop
            $machinePresent = @($machineKey.GetValueNames()) -contains $Name
        } catch {
            $machinePresent = $false
        }
        return @{
            name = $Name
            present = ($processPresent -or $userPresent -or $machinePresent)
            process_present = $processPresent
            user_present = $userPresent
            machine_present = $machinePresent
            length = $null
            value = $null
            redacted = $true
        }
    }
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ($null -eq $value) {
        $value = [Environment]::GetEnvironmentVariable($Name, "User")
    }
    if ($null -eq $value) {
        $value = [Environment]::GetEnvironmentVariable($Name, "Machine")
    }
    $present = -not [string]::IsNullOrEmpty($value)
    $record = @{
        name = $Name
        present = $present
        length = 0
        value = $null
        redacted = $SecretLike
    }
    if ($present) {
        $record.length = $value.Length
        if (-not $SecretLike) {
            $record.value = $value
        }
    }
    return $record
}

function Get-NpmConfigProbe {
    param([hashtable]$NpmProbe)
    if (-not $NpmProbe.present) {
        return @{
            present = $false
            reason = "npm command not found"
        }
    }
    return @{
        present = $true
        registry = Invoke-CommandProbe "npm" @("config", "get", "registry")
        proxy = Invoke-CommandProbe "npm" @("config", "get", "proxy")
        https_proxy = Invoke-CommandProbe "npm" @("config", "get", "https-proxy")
        strict_ssl = Invoke-CommandProbe "npm" @("config", "get", "strict-ssl")
    }
}

function Get-AppxProbe {
    try {
        $apps = Get-AppxPackage -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "OpenAI|ChatGPT" -or $_.PackageFullName -match "OpenAI|ChatGPT" } |
            Select-Object Name, PackageFullName, Version, InstallLocation
        return @{
            ok = $true
            apps = @($apps)
        }
    } catch {
        return @{
            ok = $false
            error = $_.Exception.Message
        }
    }
}

function Get-RegistryProxyProbe {
    try {
        $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        $item = Get-ItemProperty -Path $path -ErrorAction Stop
        return @{
            ok = $true
            proxy_enable = $item.ProxyEnable
            proxy_server = Convert-ToSafeString $item.ProxyServer
            proxy_override = Convert-ToSafeString $item.ProxyOverride
            auto_config_url = Convert-ToSafeString $item.AutoConfigURL
        }
    } catch {
        return @{
            ok = $false
            error = $_.Exception.Message
        }
    }
}

function Get-PathCandidateProbe {
    param([string[]]$Paths)
    $items = @()
    foreach ($candidate in $Paths) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        $exists = Test-Path -LiteralPath $candidate
        $itemType = "missing"
        if ($exists) {
            try {
                $info = Get-Item -LiteralPath $candidate -ErrorAction Stop
                if ($info.PSIsContainer) {
                    $itemType = "directory"
                } else {
                    $itemType = "file"
                }
            } catch {
                $itemType = "exists_unreadable_metadata"
            }
        }
        $items += @{
            path = $candidate
            exists = $exists
            item_type = $itemType
        }
    }
    return $items
}

function Add-UserPathDirectory {
    param([string]$Directory)
    if ([string]::IsNullOrWhiteSpace($Directory)) {
        return @{
            attempted = $false
            changed = $false
            error = "empty directory"
        }
    }
    try {
        $current = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($null -eq $current) {
            $current = ""
        }
        $parts = @($current -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        $exists = $false
        foreach ($part in $parts) {
            if ($part.TrimEnd("\") -ieq $Directory.TrimEnd("\")) {
                $exists = $true
            }
        }
        if ($exists) {
            return @{
                attempted = $true
                changed = $false
                directory = $Directory
                reason = "directory already present in user PATH"
            }
        }
        $newPath = if ([string]::IsNullOrWhiteSpace($current)) { $Directory } else { "$current;$Directory" }
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        $env:Path = "$env:Path;$Directory"
        return @{
            attempted = $true
            changed = $true
            directory = $Directory
            reason = "directory appended to user PATH; restart shells that were already open"
        }
    } catch {
        return @{
            attempted = $true
            changed = $false
            directory = $Directory
            error = $_.Exception.Message
        }
    }
}

function Get-LatestNetworkReport {
    param([string]$RunDir)
    $networkDir = Get-ChildItem -LiteralPath $RunDir -Directory -Filter "windows_openai_network_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTimeUtc -Descending |
        Select-Object -First 1
    if ($null -eq $networkDir) {
        return @{
            found = $false
        }
    }
    $jsonPath = Join-Path $networkDir.FullName "WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_REPORT.json"
    if (-not (Test-Path -LiteralPath $jsonPath)) {
        return @{
            found = $false
            directory = $networkDir.FullName
            error = "network report json not found"
        }
    }
    try {
        $report = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
        return @{
            found = $true
            directory = $networkDir.FullName
            report_path = $jsonPath
            report = $report
        }
    } catch {
        return @{
            found = $false
            directory = $networkDir.FullName
            report_path = $jsonPath
            error = $_.Exception.Message
        }
    }
}

function Add-LaunchWrappers {
    param([string]$RunDir, [object[]]$CodexExecutableCandidates)

    $codexWrapper = Join-Path $RunDir "launch_codex_clean_network_env.ps1"
    $edgeWrapper = Join-Path $RunDir "launch_chatgpt_edge_clean_profile.ps1"
    $commandsPath = Join-Path $RunDir "CANDIDATE_REPAIR_COMMANDS.txt"
    $codexLaunchCommand = "codex"
    $firstCodexCandidate = @($CodexExecutableCandidates | Where-Object { $_.exists } | Select-Object -First 1)
    if ($firstCodexCandidate.Count -gt 0) {
        $codexLaunchCommand = "& `"$($firstCodexCandidate[0].path)`""
    }

    $codexLines = @(
        'Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue',
        'Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue',
        'Remove-Item Env:ALL_PROXY -ErrorAction SilentlyContinue',
        'Remove-Item Env:http_proxy -ErrorAction SilentlyContinue',
        'Remove-Item Env:https_proxy -ErrorAction SilentlyContinue',
        'Remove-Item Env:all_proxy -ErrorAction SilentlyContinue',
        $codexLaunchCommand
    )
    $codexLines | Set-Content -Path $codexWrapper -Encoding UTF8

    $edgeLines = @(
        '$profile = Join-Path $PSScriptRoot "edge_chatgpt_clean_profile"',
        'New-Item -ItemType Directory -Force -Path $profile | Out-Null',
        '$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"',
        'if (-not (Test-Path -LiteralPath $edge)) { $edge = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe" }',
        'if (-not (Test-Path -LiteralPath $edge)) { throw "Microsoft Edge executable not found" }',
        '& $edge "--user-data-dir=$profile" "--disable-extensions" "https://chatgpt.com/"'
    )
    $edgeLines | Set-Content -Path $edgeWrapper -Encoding UTF8

    $candidateLines = @(
        "These are candidate commands only. Review before running.",
        "",
        "1. Re-run read-only network diagnostics:",
        "powershell -ExecutionPolicy Bypass -File .\scripts\diagnostics\windows_openai_network_diagnostics.ps1 -OutputRoot `"$env:USERPROFILE\Taiji_Hub\evidence`"",
        "",
        "2. Start Codex with process-local proxy variables removed:",
        "powershell -ExecutionPolicy Bypass -File `"$codexWrapper`"",
        "",
        "3. Test ChatGPT web in a clean Edge profile:",
        "powershell -ExecutionPolicy Bypass -File `"$edgeWrapper`"",
        "",
        "4. If API calls fail with 401 only, the network path is reachable and the next check is credential configuration.",
        "5. If ChatGPT web fails only in the normal browser but works in the clean profile, suspect cookies, extensions, service worker cache, or profile state.",
        "6. If DNS/TCP/TLS fails, fix the recorded DNS/proxy/VPN/security-inspection layer first."
    )
    $candidateLines | Set-Content -Path $commandsPath -Encoding UTF8

    return @{
        generated = $true
        codex_clean_network_wrapper = $codexWrapper
        chatgpt_clean_edge_wrapper = $edgeWrapper
        candidate_commands = $commandsPath
    }
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path (Get-Location) "evidence"
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$runDir = Join-Path $OutputRoot "windows_gpt_codex_repair_$timestamp"
New-SafeDirectory $runDir

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$networkScript = Join-Path $scriptRoot "windows_openai_network_diagnostics.ps1"

$commandNames = @("codex", "git", "python", "py", "node", "npm", "winget", "curl")
$commandProbes = @{}
foreach ($name in $commandNames) {
    $commandProbes[$name] = Get-CommandProbe $name
}

$versionProbes = @{
    codex = if ($commandProbes["codex"].present) { Invoke-CommandProbe "codex" @("--version") } else { @{ ok = $false; error = "codex command not found" } }
    git = if ($commandProbes["git"].present) { Invoke-CommandProbe "git" @("--version") } else { @{ ok = $false; error = "git command not found" } }
    python = if ($commandProbes["python"].present) { Invoke-CommandProbe "python" @("--version") } else { @{ ok = $false; error = "python command not found" } }
    py = if ($commandProbes["py"].present) { Invoke-CommandProbe "py" @("--version") } else { @{ ok = $false; error = "py command not found" } }
    node = if ($commandProbes["node"].present) { Invoke-CommandProbe "node" @("--version") } else { @{ ok = $false; error = "node command not found" } }
    npm = if ($commandProbes["npm"].present) { Invoke-CommandProbe "npm" @("--version") } else { @{ ok = $false; error = "npm command not found" } }
}

$envProbes = @(
    Get-EnvPresence "OPENAI_API_KEY" $true
    Get-EnvPresence "OPENAI_PROJECT" $false
    Get-EnvPresence "OPENAI_ORG_ID" $false
    Get-EnvPresence "HTTP_PROXY" $false
    Get-EnvPresence "HTTPS_PROXY" $false
    Get-EnvPresence "ALL_PROXY" $false
    Get-EnvPresence "NO_PROXY" $false
    Get-EnvPresence "http_proxy" $false
    Get-EnvPresence "https_proxy" $false
    Get-EnvPresence "all_proxy" $false
    Get-EnvPresence "no_proxy" $false
)

$codexHomeCandidates = @(
    (Join-Path $env:USERPROFILE ".codex"),
    (Join-Path $env:APPDATA "Codex"),
    (Join-Path $env:LOCALAPPDATA "Codex")
)
$codexHomes = @()
foreach ($path in $codexHomeCandidates) {
    $codexHomes += @{
        path = $path
        exists = (Test-Path -LiteralPath $path)
    }
}

$npmGlobalRoot = ""
if ($commandProbes["npm"].present) {
    $npmRootProbe = Invoke-CommandProbe "npm" @("root", "-g")
    if ($npmRootProbe.ok) {
        $npmGlobalRoot = Convert-ToSafeString $npmRootProbe.output
    }
}

$codexExecutableCandidates = @(
    (Join-Path $env:USERPROFILE ".codex\bin\codex.exe"),
    (Join-Path $env:USERPROFILE ".codex\bin\codex.cmd"),
    (Join-Path $env:USERPROFILE ".codex\bin\codex.ps1"),
    (Join-Path $env:USERPROFILE ".codex\bin\wsl\codex"),
    (Join-Path $env:APPDATA "npm\codex.cmd"),
    (Join-Path $env:APPDATA "npm\codex.ps1"),
    (Join-Path $env:LOCALAPPDATA "Programs\codex\codex.exe")
)
if (-not [string]::IsNullOrWhiteSpace($npmGlobalRoot)) {
    $codexExecutableCandidates += (Join-Path $npmGlobalRoot ".bin\codex.cmd")
    $codexExecutableCandidates += (Join-Path $npmGlobalRoot ".bin\codex.ps1")
}
$codexExecutableCandidateProbe = Get-PathCandidateProbe $codexExecutableCandidates

$userPathRepair = @{
    requested = [bool]$RepairUserPath
    attempted = $false
    changed = $false
}
if ($RepairUserPath -and (-not $commandProbes["codex"].present)) {
    $firstCodexCandidate = @($codexExecutableCandidateProbe | Where-Object { $_.exists } | Select-Object -First 1)
    if ($firstCodexCandidate.Count -gt 0) {
        $candidateDirectory = Split-Path -Parent $firstCodexCandidate[0].path
        $userPathRepair = Add-UserPathDirectory $candidateDirectory
        $userPathRepair["requested"] = $true
    } else {
        $userPathRepair = @{
            requested = $true
            attempted = $false
            changed = $false
            reason = "no Codex executable candidate found"
        }
    }
}

$postRepairCommandProbes = @{}
foreach ($name in $commandNames) {
    $postRepairCommandProbes[$name] = Get-CommandProbe $name
}
$postRepairVersionProbes = @{
    codex = if ($postRepairCommandProbes["codex"].present) { Invoke-CommandProbe "codex" @("--version") } else { @{ ok = $false; error = "codex command not found" } }
}

$networkInvocation = @{
    attempted = $false
    ok = $false
    output = ""
    error = ""
}
if (Test-Path -LiteralPath $networkScript) {
    $networkInvocation.attempted = $true
    try {
        $networkOutput = & $networkScript -OutputRoot $runDir -TimeoutSec $TimeoutSec 2>&1
        $networkInvocation.ok = $true
        $networkInvocation.output = Convert-ToSafeString $networkOutput
    } catch {
        $networkInvocation.ok = $false
        $networkInvocation.error = $_.Exception.Message
    }
} else {
    $networkInvocation.error = "network diagnostic script not found: $networkScript"
}

$networkReport = Get-LatestNetworkReport $runDir
$npmConfig = Get-NpmConfigProbe $commandProbes["npm"]
$appxProbe = Get-AppxProbe
$registryProxy = Get-RegistryProxyProbe

$observations = @()
$repairCandidates = @()
if (-not $postRepairCommandProbes["codex"].present) {
    $observations += "Codex CLI command is not discoverable in PATH."
    $repairCandidates += "Install Codex CLI or add the existing Codex executable directory to the current user's PATH."
    $existingCodexCandidates = @($codexExecutableCandidateProbe | Where-Object { $_.exists })
    if ($existingCodexCandidates.Count -gt 0) {
        $observations += "Codex executable candidate exists outside PATH."
        $repairCandidates += "Add the discovered Codex executable directory to PATH or launch it directly from the recorded candidate path."
    }
} elseif (-not $commandProbes["codex"].present) {
    $observations += "Codex CLI became discoverable in the current diagnostic process after PATH repair."
}
if ($userPathRepair.changed) {
    $observations += "Codex candidate directory was appended to current user's PATH."
    $repairCandidates += "Restart already-open Windows shells if they still cannot see codex; this diagnostic process refreshed its PATH view."
}
if (-not $postRepairCommandProbes["node"].present) {
    $observations += "Node.js command is not discoverable in PATH; npm-based Codex installs or helpers may fail."
    $repairCandidates += "Install or repair Node.js/npm if this Codex installation path depends on npm."
}
if (-not (($envProbes | Where-Object { $_.name -eq "OPENAI_API_KEY" }).present)) {
    $observations += "OPENAI_API_KEY is not present in process/user/machine environment; API calls may return authentication errors even when network is reachable."
    $repairCandidates += "Configure an OpenAI API key in the intended process/user environment if API-backed Codex or scripts require it."
}
$proxySignals = @($envProbes | Where-Object { $_.name -match "proxy" -and $_.present })
if ($proxySignals.Count -gt 0 -or ($registryProxy.ok -and $registryProxy.proxy_enable)) {
    $observations += "Proxy settings are present; compare WinHTTP, browser proxy, and environment proxy values."
    $repairCandidates += "Test Codex with launch_codex_clean_network_env.ps1 to isolate process-level proxy pollution."
}

if ($networkReport.found) {
    foreach ($endpoint in $networkReport.report.endpoints) {
        if (-not $endpoint.dns.ok) {
            $observations += "$($endpoint.host): DNS resolution failed."
            $repairCandidates += "Fix DNS resolver path for $($endpoint.host) before changing Codex or browser settings."
        } elseif (-not $endpoint.tcp_443.tcp_test_succeeded) {
            $observations += "$($endpoint.host): TCP 443 failed after DNS succeeded."
            $repairCandidates += "Check firewall, VPN, router, or ISP path for TCP 443 to $($endpoint.host)."
        } elseif (-not $endpoint.tls.ok) {
            $observations += "$($endpoint.host): TLS handshake failed after TCP 443 succeeded."
            $repairCandidates += "Check TLS inspection, security software, or certificate interception for $($endpoint.host)."
        } elseif ($endpoint.https_head.status_code -eq 403) {
            $observations += "$($endpoint.host): HTTPS reachable but returned 403/challenge; suspect browser profile, VPN/proxy reputation, security inspection, or anti-bot challenge."
            $repairCandidates += "Use launch_chatgpt_edge_clean_profile.ps1 for ChatGPT/auth challenge isolation."
        } elseif ($endpoint.https_head.status_code -eq 401) {
            $observations += "$($endpoint.host): HTTPS reachable; authentication is required."
            $repairCandidates += "Treat 401 from API as network-reachable and continue with credential/configuration checks."
        } elseif ($endpoint.https_head.status_code -eq 404) {
            $observations += "$($endpoint.host): HTTPS reachable; root path returned 404."
        } elseif ($endpoint.https_head.ok) {
            $observations += "$($endpoint.host): HTTPS reachable."
        } else {
            $observations += "$($endpoint.host): HTTPS request failed: $($endpoint.https_head.error)"
        }
    }
}

$safeFixes = @{
    requested = [bool]$ApplySafeFixes
    generated = $false
}
if ($ApplySafeFixes) {
    $safeFixes = Add-LaunchWrappers $runDir $codexExecutableCandidateProbe
    $safeFixes["requested"] = $true
}

$report = @{
    schema = "TAIJI_WINDOWS_GPT_CODEX_REPAIR_DIAGNOSTIC_V1"
    state = "DIAGNOSTIC_COMPLETE"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    purpose = "Diagnose why GPT, ChatGPT, or Codex is not running normally on local Windows."
    side_effects = @{
        installs_packages = $false
        changes_network_settings = $false
        changes_firewall = $false
        reads_secret_values = $false
        external_api_mutation = $false
        writes_evidence_files = $true
        generated_candidate_wrappers = [bool]$ApplySafeFixes
        changes_user_path = [bool]$userPathRepair.changed
    }
    execution_context = @{
        user = $env:USERNAME
        computer = $env:COMPUTERNAME
        user_profile = $env:USERPROFILE
        powershell_version = Convert-ToSafeString $PSVersionTable.PSVersion
        execution_policy = Convert-ToSafeString (Get-ExecutionPolicy -List)
    }
    commands = $commandProbes
    versions = $versionProbes
    post_repair_commands = $postRepairCommandProbes
    post_repair_versions = $postRepairVersionProbes
    environment = $envProbes
    codex_local_state = @{
        home_candidates = $codexHomes
        executable_candidates = $codexExecutableCandidateProbe
        npm_global_root = $npmGlobalRoot
    }
    windows_apps = $appxProbe
    proxy = @{
        registry_current_user = $registryProxy
        npm = $npmConfig
    }
    network_diagnostics = @{
        invocation = $networkInvocation
        latest_report = if ($networkReport.found) { @{
            found = $true
            directory = $networkReport.directory
            report_path = $networkReport.report_path
        } } else { $networkReport }
    }
    observations = $observations
    repair_candidates = @($repairCandidates | Select-Object -Unique)
    user_path_repair = $userPathRepair
    safe_fixes = $safeFixes
}

$jsonPath = Join-Path $runDir "WINDOWS_GPT_CODEX_REPAIR_REPORT.json"
$textPath = Join-Path $runDir "WINDOWS_GPT_CODEX_REPAIR_SUMMARY.txt"
$sealPath = Join-Path $runDir "EVIDENCE_SEAL.txt"

$report | ConvertTo-Json -Depth 30 | Set-Content -Path $jsonPath -Encoding UTF8

$summaryLines = @()
$summaryLines += "TAIJI_WINDOWS_GPT_CODEX_REPAIR_DIAGNOSTIC_V1"
$summaryLines += "generated_at_utc=$($report.generated_at_utc)"
$summaryLines += "user=$($env:USERNAME)"
$summaryLines += "computer=$($env:COMPUTERNAME)"
$summaryLines += "side_effects.installs_packages=false"
$summaryLines += "side_effects.changes_network_settings=false"
$summaryLines += "side_effects.reads_secret_values=false"
$summaryLines += "side_effects.changes_user_path=$([bool]$userPathRepair.changed)"
$summaryLines += "codex_initial_present=$($commandProbes["codex"].present)"
$summaryLines += "codex_post_repair_present=$($postRepairCommandProbes["codex"].present)"
$summaryLines += "codex_post_repair_version_ok=$($postRepairVersionProbes["codex"].ok)"
$summaryLines += ""
$summaryLines += "observations:"
foreach ($line in $observations) {
    $summaryLines += "- $line"
}
$summaryLines += ""
$summaryLines += "repair_candidates:"
foreach ($line in @($repairCandidates | Select-Object -Unique)) {
    $summaryLines += "- $line"
}
$summaryLines += ""
$summaryLines += "outputs:"
$summaryLines += "- report=$jsonPath"
$summaryLines += "- summary=$textPath"
if ($ApplySafeFixes) {
    $summaryLines += "- safe_fix_wrappers=$($safeFixes | ConvertTo-Json -Compress)"
}
$summaryLines | Set-Content -Path $textPath -Encoding UTF8

$jsonHash = (Get-FileHash -Algorithm SHA256 -Path $jsonPath).Hash.ToLowerInvariant()
$textHash = (Get-FileHash -Algorithm SHA256 -Path $textPath).Hash.ToLowerInvariant()
$sealContent = @(
    "schema=TAIJI_WINDOWS_GPT_CODEX_REPAIR_EVIDENCE_SEAL_V1",
    "generated_at_utc=$((Get-Date).ToUniversalTime().ToString("o"))",
    "report=$jsonPath",
    "report_sha256=$jsonHash",
    "summary=$textPath",
    "summary_sha256=$textHash",
    "side_effects.installs_packages=false",
    "side_effects.changes_network_settings=false",
    "side_effects.changes_firewall=false",
    "side_effects.reads_secret_values=false",
    "side_effects.external_api_mutation=false",
    "side_effects.changes_user_path=$([bool]$userPathRepair.changed)"
)
$sealContent | Set-Content -Path $sealPath -Encoding UTF8

Write-Output "STATE=DIAGNOSTIC_COMPLETE"
Write-Output "REPORT=$jsonPath"
Write-Output "SUMMARY=$textPath"
Write-Output "SEAL=$sealPath"
Write-Output "REPORT_SHA256=$jsonHash"
