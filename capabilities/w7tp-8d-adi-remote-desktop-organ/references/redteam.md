# Red Team（紅隊）－Remote Desktop Commander（遠端桌面指揮官）等價重構

1. 不把「工具很多」當成「權限很大」：每個能力分別分類。
2. 不把 `start_process（啟動程序）` 固定標安全：命令本體決定作用類別。
3. 不把 Remote Desktop Commander offline（離線）當節點 offline（離線）。
4. 不把 PID（程序識別碼）當穩定身份；作用前後都需重新定位。
5. 不把成功 exit code（離開碼）當實際效果成功；需要重新觀測目標狀態。
6. 不把外部工具的使用者／管理員身份當 Founder／組織 D8。
7. 不把 IP、Tailscale、LAN 可達性當服務身份或權威。
8. 不讓 Command Cache（指令快取）直接呼叫 destructive effect（破壞性作用）；仍經 D8。
9. 不讓雲端補全寫入「事實」或「權威」；只能回候選。
10. 不要求所有本地檔案／UI 讀取都走生成式狀態傳輸；D6 用於跨節點／跨組織狀態重構，原胞封包是可用機制之一；差異分析不是傳輸技術。
11. 不以兼容層永久綁死外部 runtime；Native Target（原生目標）應可由 native_claw 提供。
12. 不把 native_claw 當第二個決策引擎；它只是最後作用器。
