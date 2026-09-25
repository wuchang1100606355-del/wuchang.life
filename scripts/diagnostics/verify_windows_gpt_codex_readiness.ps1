param(
    [string]$OutputRoot = "",
    [int]$TimeoutSec = 20
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

function Test-Dns {
    param([string]$HostName)
    try {
        $records = Resolve-DnsName -Name $HostName -ErrorAction Stop |
            Where-Object { $_.IPAddress -or $_.NameHost } |
            Select-Object Type, Name, IPAddress, NameHost
        return @{
            ok = $true
            host = $HostName
            records = @($records)
        }
    } catch {
        return @{
            ok = $false
            host = $HostName
            error = $_.Exception.Message
        }
    }
}

function Test-Tcp443 {
    param([string]$HostName)
    try {
        $result = Test-NetConnection -ComputerName $HostName -Port 443 -InformationLevel Detailed -WarningAction SilentlyContinue
        return @{
            ok = [bool]$result.TcpTestSucceeded
            host = $HostName
            remote_address = Convert-ToSafeString $result.RemoteAddress
            tcp_test_succeeded = [bool]$result.TcpTestSucceeded
            interface_alias = Convert-ToSafeString $result.InterfaceAlias
            source_address = Convert-ToSafeString $result.SourceAddress
        }
    } catch {
        return @{
            ok = $false
            host = $HostName
            error = $_.Exception.Message
        }
    }
}

function Test-TlsHandshake {
    param([string]$HostName)
    $client = $null
    $stream = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $connectTask = $client.ConnectAsync($HostName, 443)
        if (-not $connectTask.Wait($TimeoutSec * 1000)) {
            throw "TCP connect timeout"
        }
        $stream = New-Object System.Net.Security.SslStream($client.GetStream(), $false, ({ $true } -as [Net.Security.RemoteCertificateValidationCallback]))
        $stream.AuthenticateAsClient($HostName)
        $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($stream.RemoteCertificate)
        return @{
            ok = $true
            host = $HostName
            ssl_protocol = Convert-ToSafeString $stream.SslProtocol
            certificate_subject = Convert-ToSafeString $cert.Subject
            certificate_issuer = Convert-ToSafeString $cert.Issuer
            certificate_not_after = $cert.NotAfter.ToUniversalTime().ToString("o")
        }
    } catch {
        return @{
            ok = $false
            host = $HostName
            error = $_.Exception.Message
        }
    } finally {
        if ($stream) { $stream.Dispose() }
        if ($client) { $client.Dispose() }
    }
}

function Test-HttpsHead {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Head -TimeoutSec $TimeoutSec -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop
        return @{
            ok = $true
            url = $Url
            status_code = [int]$response.StatusCode
            status_description = Convert-ToSafeString $response.StatusDescription
            headers = $response.Headers
        }
    } catch {
        $statusCode = $null
        $headers = @{}
        if ($_.Exception.Response) {
            try {
                $statusCode = [int]$_.Exception.Response.StatusCode
                $headers = $_.Exception.Response.Headers
            } catch {
                $statusCode = $null
            }
        }
        return @{
            ok = $false
            url = $Url
            status_code = $statusCode
            error = $_.Exception.Message
            headers = $headers
        }
    }
}

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $env:USERPROFILE "Taiji_Hub\evidence"
}
New-SafeDirectory $OutputRoot

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$runDir = Join-Path $OutputRoot "windows_gpt_codex_readiness_$timestamp"
New-SafeDirectory $runDir

$codexCommand = Get-Command codex -ErrorAction SilentlyContinue
$codexProbe = @{
    present = $false
    path = ""
    version = @{
        ok = $false
        error = "codex command not found"
    }
}
if ($null -ne $codexCommand) {
    $codexProbe.present = $true
    $codexProbe.path = Convert-ToSafeString $codexCommand.Source
    $codexProbe.version = Invoke-CommandProbe "codex" @("--version")
}

$endpoints = @(
    @{ name = "openai_api"; host = "api.openai.com"; url = "https://api.openai.com/v1/models"; pass_statuses = @(200, 401) },
    @{ name = "chatgpt_web"; host = "chatgpt.com"; url = "https://chatgpt.com/"; pass_statuses = @(200, 301, 302, 401, 403) },
    @{ name = "openai_auth"; host = "auth.openai.com"; url = "https://auth.openai.com/"; pass_statuses = @(200, 301, 302, 401, 403) }
)

$endpointResults = @()
foreach ($endpoint in $endpoints) {
    $https = Test-HttpsHead $endpoint.url
    $status = $https.status_code
    $endpointResults += @{
        name = $endpoint.name
        host = $endpoint.host
        url = $endpoint.url
        dns = Test-Dns $endpoint.host
        tcp_443 = Test-Tcp443 $endpoint.host
        tls = Test-TlsHandshake $endpoint.host
        https_head = $https
        readiness_ok = ($endpoint.pass_statuses -contains $status)
    }
}

$apiEndpoint = @($endpointResults | Where-Object { $_.name -eq "openai_api" } | Select-Object -First 1)
$chatgptEndpoint = @($endpointResults | Where-Object { $_.name -eq "chatgpt_web" } | Select-Object -First 1)
$authEndpoint = @($endpointResults | Where-Object { $_.name -eq "openai_auth" } | Select-Object -First 1)

$failures = @()
$warnings = @()
if (-not $codexProbe.present) {
    $failures += "codex_command_missing"
} elseif (-not $codexProbe.version.ok) {
    $failures += "codex_version_failed"
}
if (-not $apiEndpoint.readiness_ok) {
    $failures += "openai_api_not_ready"
}
if (-not $chatgptEndpoint.readiness_ok) {
    $warnings += "chatgpt_web_not_ready"
} elseif ($chatgptEndpoint.https_head.status_code -eq 403) {
    $warnings += "chatgpt_web_challenge_present"
}
if (-not $authEndpoint.readiness_ok) {
    $warnings += "openai_auth_not_ready"
} elseif ($authEndpoint.https_head.status_code -eq 403) {
    $warnings += "openai_auth_challenge_present"
}

$state = if ($failures.Count -eq 0) { "PASS_WINDOWS_GPT_CODEX_READINESS" } else { "HOLD_WINDOWS_GPT_CODEX_READINESS" }

$report = @{
    schema = "TAIJI_WINDOWS_GPT_CODEX_READINESS_V1"
    state = $state
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    side_effects = @{
        installs_packages = $false
        changes_network_settings = $false
        changes_user_path = $false
        reads_secret_values = $false
        external_api_mutation = $false
    }
    codex = $codexProbe
    endpoints = $endpointResults
    failures = $failures
    warnings = $warnings
}

$jsonPath = Join-Path $runDir "WINDOWS_GPT_CODEX_READINESS_REPORT.json"
$textPath = Join-Path $runDir "WINDOWS_GPT_CODEX_READINESS_SUMMARY.txt"
$sealPath = Join-Path $runDir "READINESS_EVIDENCE_SEAL.txt"

$report | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

$summary = @(
    "TAIJI_WINDOWS_GPT_CODEX_READINESS_V1",
    "generated_at_utc=$($report.generated_at_utc)",
    "state=$state",
    "codex_present=$($codexProbe.present)",
    "codex_version_ok=$($codexProbe.version.ok)",
    "openai_api_status=$($apiEndpoint.https_head.status_code)",
    "chatgpt_web_status=$($chatgptEndpoint.https_head.status_code)",
    "openai_auth_status=$($authEndpoint.https_head.status_code)",
    "failures=$($failures -join ',')",
    "warnings=$($warnings -join ',')"
)
$summary | Set-Content -Path $textPath -Encoding UTF8

$jsonHash = (Get-FileHash -Algorithm SHA256 -Path $jsonPath).Hash.ToLowerInvariant()
$textHash = (Get-FileHash -Algorithm SHA256 -Path $textPath).Hash.ToLowerInvariant()
$seal = @(
    "schema=TAIJI_WINDOWS_GPT_CODEX_READINESS_SEAL_V1",
    "generated_at_utc=$((Get-Date).ToUniversalTime().ToString("o"))",
    "readiness_report=$jsonPath",
    "readiness_report_sha256=$jsonHash",
    "readiness_summary=$textPath",
    "readiness_summary_sha256=$textHash",
    "side_effects.installs_packages=false",
    "side_effects.changes_network_settings=false",
    "side_effects.changes_user_path=false",
    "side_effects.reads_secret_values=false",
    "side_effects.external_api_mutation=false"
)
$seal | Set-Content -Path $sealPath -Encoding UTF8

Write-Output "STATE=$state"
Write-Output "READINESS_REPORT=$jsonPath"
Write-Output "READINESS_SUMMARY=$textPath"
Write-Output "READINESS_SEAL=$sealPath"
