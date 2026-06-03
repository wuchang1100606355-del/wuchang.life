請以五常智慧雲正式主控場 ~/Taiji_Hub 為唯一 canonical workspace 進行 code review。
請檢查：
1. 目前 9002 Gateway 是否仍綁在 legacy ~/wuchang_8_0_core。
2. 是否應遷移到 ~/Taiji_Hub/services/gateway。
3. commander、W7TP、Odoo 候選包、runtime/broadcast 是否路徑一致。
4. 哪些檔案可以只讀遷移，哪些不可再 patch。
5. 請輸出最小變更方案，不要 kill process，不要改 DB，不要輸出 secret。
