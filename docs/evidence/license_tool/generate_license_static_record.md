# generate_license.exe 靜態證據紀錄

## 檔案定位
generate_license.exe 為授權產生工具候選，屬高敏感可執行檔。僅作靜態封存與證據鏈紀錄，不得直接於主系統裸跑。

## Hash
SHA256: f9fc5ad5cf3fc48bec33722c927eda6f8b5f51bedb40179548a1903acaf70507
SHA1: 04127335fafdf0972bfe062ca7bcab44e0c749ed
MD5: c51c6464126521559afe0ee7147c9c0d

## 靜態判讀
- Windows PE32+ x86-64 console executable
- 匯入 USER32.dll / KERNEL32.dll / ADVAPI32.dll
- 具程序、檔案、環境變數、權限 token 相關 API 能力

## 紅隊邊界
- 不直接執行
- 不公開散布
- 不放入專利公開附件
- 不與任何 key/token/private key 混放
- 測試限離線 VM / Windows Sandbox
