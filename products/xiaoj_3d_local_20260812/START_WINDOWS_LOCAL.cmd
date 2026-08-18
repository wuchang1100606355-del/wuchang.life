@echo off
setlocal
set "XIAOJ_DIR=/home/taiji_admin/Taiji_Hub/products/xiaoj_3d_local_20260812"
start "Xiao J 3D Local Server" /min wsl.exe -e bash -lc "cd '%XIAOJ_DIR%' && python3 launcher.py"
powershell.exe -NoProfile -Command "Start-Sleep -Milliseconds 1200; Start-Process 'http://127.0.0.1:4173/'"
endlocal
