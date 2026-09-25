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
    return ($Value | Out-String).Trim()
}

function Get-CommandOutput {
    param([string]$FilePath, [string[]]$Arguments)
    try {
        $output = & $FilePath @Arguments 2>&1
        return @{
            ok = $true
            command = "$FilePath $($Arguments -join ' ')"
            output = Convert-ToSafeString $output
        }
    } catch {
        return @{
            ok = $false
            command = "$FilePath $($Arguments -join ' ')"
            error = $_.Exception.Message
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
            resolved_addresses = @($result.ResolvedAddresses | ForEach-Object { Convert-ToSafeString $_ })
            tcp_test_succeeded = [bool]$result.TcpTestSucceeded
            interface_alias = Convert-ToSafeString $result.InterfaceAlias
            source_address = Convert-ToSafeString $result.SourceAddress
            net_route_next_hop = Convert-ToSafeString $result.NetRoute.NextHop
        }
    } catch {
        return @{
            ok = $false
            host = $HostName
            error = $_.Exception.Message
        }
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
            cipher_algorithm = Convert-ToSafeString $stream.CipherAlgorithm
            cipher_strength = [int]$stream.CipherStrength
            certificate_subject = Convert-ToSafeString $cert.Subject
            certificate_issuer = Convert-ToSafeString $cert.Issuer
            certificate_not_after = $cert.NotAfter.ToUniversalTime().ToString("o")
            certificate_thumbprint = Convert-ToSafeString $cert.Thumbprint
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

if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path (Get-Location) "evidence"
}

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
$runDir = Join-Path $OutputRoot "windows_openai_network_$timestamp"
New-SafeDirectory $runDir

$endpoints = @(
    @{ name = "openai_api"; host = "api.openai.com"; url = "https://api.openai.com/v1/models"; expected = "401 without API key means network path is reachable" },
    @{ name = "chatgpt_web"; host = "chatgpt.com"; url = "https://chatgpt.com/"; expected = "200, 3xx, 401, or Cloudflare challenge can still prove reachability" },
    @{ name = "openai_auth"; host = "auth.openai.com"; url = "https://auth.openai.com/"; expected = "200, 3xx, 401, or Cloudflare challenge can still prove reachability" },
    @{ name = "openai_static"; host = "cdn.oaistatic.com"; url = "https://cdn.oaistatic.com/"; expected = "404 at root can still prove CDN reachability" },
    @{ name = "openai_files"; host = "files.oaiusercontent.com"; url = "https://files.oaiusercontent.com/"; expected = "404 at root can still prove file CDN reachability" },
    @{ name = "chatgpt_ab"; host = "ab.chatgpt.com"; url = "https://ab.chatgpt.com/"; expected = "200, 3xx, 403, or 404 can still prove reachability" }
)

$proxyEnv = @{
    HTTP_PROXY = $env:HTTP_PROXY
    HTTPS_PROXY = $env:HTTPS_PROXY
    ALL_PROXY = $env:ALL_PROXY
    NO_PROXY = $env:NO_PROXY
    http_proxy = $env:http_proxy
    https_proxy = $env:https_proxy
    all_proxy = $env:all_proxy
    no_proxy = $env:no_proxy
}

$system = @{
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    user = $env:USERNAME
    computer = $env:COMPUTERNAME
    os = Convert-ToSafeString (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture)
    powershell_version = Convert-ToSafeString $PSVersionTable.PSVersion
    execution_policy = Convert-ToSafeString (Get-ExecutionPolicy -List)
}

$network = @{
    ip_configuration = Convert-ToSafeString (Get-NetIPConfiguration)
    dns_client_servers = Convert-ToSafeString (Get-DnsClientServerAddress)
    winhttp_proxy = Get-CommandOutput "netsh" @("winhttp", "show", "proxy")
    environment_proxy = $proxyEnv
    route_0 = Convert-ToSafeString (Get-NetRoute -DestinationPrefix "0.0.0.0/0" -ErrorAction SilentlyContinue)
    route_v6 = Convert-ToSafeString (Get-NetRoute -DestinationPrefix "::/0" -ErrorAction SilentlyContinue)
}

$endpointResults = @()
foreach ($endpoint in $endpoints) {
    $endpointResults += @{
        name = $endpoint.name
        host = $endpoint.host
        url = $endpoint.url
        expected = $endpoint.expected
        dns = Test-Dns $endpoint.host
        tcp_443 = Test-Tcp443 $endpoint.host
        tls = Test-TlsHandshake $endpoint.host
        https_head = Test-HttpsHead $endpoint.url
    }
}

$diagnosis = @()
foreach ($result in $endpointResults) {
    if (-not $result.dns.ok) {
        $diagnosis += "$($result.host): DNS resolution failed"
    } elseif (-not $result.tcp_443.tcp_test_succeeded) {
        $diagnosis += "$($result.host): TCP 443 failed after DNS succeeded"
    } elseif (-not $result.tls.ok) {
        $diagnosis += "$($result.host): TLS handshake failed after TCP 443 succeeded"
    } elseif ($result.https_head.status_code -eq 403) {
        $diagnosis += "$($result.host): HTTPS reachable, but returned 403/challenge; check browser, cookies, VPN/proxy reputation, or security inspection"
    } elseif ($result.https_head.status_code -eq 401) {
        $diagnosis += "$($result.host): HTTPS reachable, authentication required"
    } elseif ($result.https_head.status_code -eq 404) {
        $diagnosis += "$($result.host): HTTPS reachable, root path not found"
    } elseif ($result.https_head.ok) {
        $diagnosis += "$($result.host): HTTPS reachable"
    } else {
        $diagnosis += "$($result.host): HTTPS request failed: $($result.https_head.error)"
    }
}

$report = @{
    schema = "TAIJI_WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_V1"
    state = "DIAGNOSTIC_COMPLETE"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    side_effects = @{
        installs_packages = $false
        changes_network_settings = $false
        reads_secrets = $false
        external_api_mutation = $false
    }
    system = $system
    network = $network
    endpoints = $endpointResults
    diagnosis = $diagnosis
}

$jsonPath = Join-Path $runDir "WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_REPORT.json"
$textPath = Join-Path $runDir "WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_SUMMARY.txt"
$sealPath = Join-Path $runDir "EVIDENCE_SEAL.txt"

$report | ConvertTo-Json -Depth 20 | Set-Content -Path $jsonPath -Encoding UTF8

$summaryLines = @()
$summaryLines += "TAIJI_WINDOWS_OPENAI_NETWORK_DIAGNOSTIC_V1"
$summaryLines += "generated_at_utc=$($report.generated_at_utc)"
$summaryLines += "user=$($system.user)"
$summaryLines += "computer=$($system.computer)"
$summaryLines += ""
$summaryLines += "diagnosis:"
foreach ($line in $diagnosis) {
    $summaryLines += "- $line"
}
$summaryLines | Set-Content -Path $textPath -Encoding UTF8

$jsonHash = (Get-FileHash -Algorithm SHA256 -Path $jsonPath).Hash.ToLowerInvariant()
$textHash = (Get-FileHash -Algorithm SHA256 -Path $textPath).Hash.ToLowerInvariant()
$sealContent = @(
    "schema=TAIJI_WINDOWS_OPENAI_NETWORK_EVIDENCE_SEAL_V1",
    "generated_at_utc=$((Get-Date).ToUniversalTime().ToString("o"))",
    "report=$jsonPath",
    "report_sha256=$jsonHash",
    "summary=$textPath",
    "summary_sha256=$textHash",
    "side_effects.installs_packages=false",
    "side_effects.changes_network_settings=false",
    "side_effects.reads_secrets=false",
    "side_effects.external_api_mutation=false"
)
$sealContent | Set-Content -Path $sealPath -Encoding UTF8

Write-Output "STATE=DIAGNOSTIC_COMPLETE"
Write-Output "REPORT=$jsonPath"
Write-Output "SUMMARY=$textPath"
Write-Output "SEAL=$sealPath"
Write-Output "REPORT_SHA256=$jsonHash"
