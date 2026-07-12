# WSL 登入啟動檔案與標題說明

STATE=WSL_LOGIN_STARTUP_ENTRY_README
RUN_ID=WSL_STARTUP_TITLE_CN_PATCH_P1_20260706T170643Z

## 中文標題

太極登入唯讀檢查｜目前狀態

## 啟動流程

```text
PowerShell / Windows Terminal
→ wsl
→ Ubuntu bash interactive shell
→ shell startup file
→ Taiji Login Readonly Check
```

## 已更新檔案

- /home/taiji_admin/Taiji_Hub/boot/taiji_login_readonly_check.sh

## 備份位置

runtime/total_field/wsl_startup_title_cn/WSL_STARTUP_TITLE_CN_PATCH_P1_20260706T170643Z/backups

## 安全邊界

- 僅修改登入標題文字
- 未 deploy
- 未 restart
- 未 DB write
- 未讀取 token/key
- 未改服務啟動狀態

## 生效方式

關閉目前 WSL 終端後重新輸入 wsl，即可看到中文標題。
