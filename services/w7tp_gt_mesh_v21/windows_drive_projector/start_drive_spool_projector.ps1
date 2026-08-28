[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$DriveRoot,

    [string]$SpoolDir = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'W7TP\gt_mesh_v21\drive_spool'),

    [string]$ReceiptDir = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'W7TP\gt_mesh_v21\receipts'),

    [string]$PythonExe = 'py',

    [switch]$Watch,

    [ValidateRange(1, 3600)]
    [int]$PollSeconds = 5
)

$ErrorActionPreference = 'Stop'
$projector = Join-Path $PSScriptRoot 'drive_spool_projector.py'

if (-not (Test-Path -LiteralPath $projector -PathType Leaf)) {
    throw "Projector entrypoint is missing: $projector"
}
if (-not (Test-Path -LiteralPath $DriveRoot -PathType Container)) {
    throw "Drive 8D_ADI_INDEX root must already exist: $DriveRoot"
}
if (-not (Test-Path -LiteralPath $SpoolDir -PathType Container)) {
    throw "Local append-only spool must already exist: $SpoolDir"
}

New-Item -ItemType Directory -Path $ReceiptDir -Force | Out-Null

$arguments = @(
    '-3',
    $projector,
    '--drive-root', $DriveRoot,
    '--spool-dir', $SpoolDir,
    '--receipt-dir', $ReceiptDir
)

if ($Watch) {
    $arguments += @('--watch', '--poll-seconds', $PollSeconds)
}

& $PythonExe @arguments
exit $LASTEXITCODE
