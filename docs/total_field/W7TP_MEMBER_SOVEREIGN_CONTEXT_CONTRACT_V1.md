# T-011A Member Sovereign Context Contract（會員主權上下文契約）

狀態：`CANDIDATE_CONTRACT_READY`

本層不是新會員系統核心，而是把既有會員主權證據投影成 T-011 可使用的最小、ref-only（僅引用）Dynamic Context（動態上下文）。

## 既有能力沿用

沿用既有：

- Member Sovereign Identity Root（會員主權身分根）契約與驗證器。
- Member Session / Scene / Consent / Role Seat（會員工作階段／場景／同意／角色席位）衍生封包。
- P3 Session Dual Receipt Gate（工作階段雙收據閘門）。
- MEMBER_SOVEREIGNTY_NON_OVERRIDE_POLICY（會員主權不可覆蓋政策）。
- Total Field Dynamic Context Pull（總場動態上下文拉取）既有 model-visible context（模型可見上下文）形狀。

沒有建立第二套身分根、8D、D8、GST 或 Total Field。

## 固定語義

`Natural Person（自然人） != Seat（席位）`

`Organization Request（組織請求） != Member Authorization（會員授權）`

Odoo 仍只是 process / masked projection（流程／遮罩投影），不是自然人主權根。

一般會員敏感工作目前只接受既有 member-consent dual-receipt（會員同意雙收據）已 PASS 的路徑。依法另有處理依據的 legal-basis path（法定依據路徑）已保留語義位置，但在既有 legal-basis verifier（法定依據驗證器）綁定前一律 HOLD，不由本 adapter 自創裁決。

## 模型可見資料

只投影：

- natural_person_ref
- identity_root_ref
- organization_ref
- seat_ref
- role_ref
- session_ref
- scene_ref
- organization_request_ref
- member_authorization_ref
- purpose_ref
- scope_refs
- time window
- capability refs
- audit / risk / gate / receipt refs

不投影會員明文、憑證、token（權杖）、秘密或重構規則。

## 權威

LLM（大型語言模型）、MSI、Codex、Chrome 都只接收候選所需最小上下文；正式效果仍回既有 taiji01 Total Field（總場）。

本候選不修改 runtime（執行環境）、不部署、不重啟服務、不改 pointer（指標），也不碰 T-014。
