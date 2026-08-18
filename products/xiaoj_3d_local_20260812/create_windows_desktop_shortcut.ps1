$desktop = [Environment]::GetFolderPath('Desktop')
$cmd = Join-Path $desktop 'Launch Xiao J 3D Local.cmd'
$link = Join-Path $desktop 'Xiao J 3D Local.lnk'
$content = @'
@echo off
start "" /min wsl.exe -e bash -lc "cd '/home/taiji_admin/Taiji_Hub/products/xiaoj_3d_local_20260812' && python3 launcher.py"
powershell.exe -NoProfile -Command "Start-Sleep -Milliseconds 1200; Start-Process 'http://127.0.0.1:4173/'"
'@
[IO.File]::WriteAllText($cmd, $content, (New-Object Text.UTF8Encoding($false)))
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $env:ComSpec
$shortcut.Arguments = '/c "' + $cmd + '"'
$shortcut.WorkingDirectory = $desktop
$shortcut.IconLocation = $env:SystemRoot + '\System32\shell32.dll,220'
$shortcut.Description = 'Launch the local Xiao J 3D product and open its browser view.'
$shortcut.Save()
Start-Process 'http://127.0.0.1:4173/'
Write-Output $cmd
Write-Output $link
