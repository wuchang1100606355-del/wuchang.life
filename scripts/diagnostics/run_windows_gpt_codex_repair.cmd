@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."
set "OUTPUT_ROOT=%USERPROFILE%\Taiji_Hub\evidence"
if defined TAIJI_WINDOWS_SYNC_ROOT (
  set "SYNC_ROOT=%TAIJI_WINDOWS_SYNC_ROOT%"
) else (
  set "SYNC_ROOT=%REPO_ROOT%\evidence_from_windows"
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_windows_gpt_codex_full_repair.ps1" -OutputRoot "%OUTPUT_ROOT%" -SyncEvidenceRoot "%SYNC_ROOT%" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ExitCode=%EXIT_CODE%
echo EvidenceRoot=%OUTPUT_ROOT%
echo SyncRoot=%SYNC_ROOT%
exit /b %EXIT_CODE%
