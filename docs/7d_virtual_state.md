# 7D Virtual State

7D 虛擬狀態層是 Real State 與 AI 推演之間的隔離層。

AI 不直接操作真實 Odoo / IO / POS / member state，而是先操作投影後的 virtual state。

## Flow

IO_event -> TEFMP packet -> Virtual State -> AI Derivation -> Metric Gate -> Commit / Rollback

## Rule

Cloud AI can derive.
Cloud AI cannot touch real state.
Commit requires metric gate and audit.
