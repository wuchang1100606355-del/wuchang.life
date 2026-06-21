# W7TP_REDTEAM_ALERT_OMISSION_INTEGRITY_RULE_20260621T160754Z

STATE=TOTAL_FIELD_REDTEAM_ALERT_OMISSION_INTEGRITY_RULE_RECORDED  
CLASSIFICATION=GOVERNANCE_RULE_ADDENDUM

## Rule

凡已滿足告警條件而未告警，視為總場信任違規。

If DETOUR_ALERT_CRITICAL or SIMPLIFICATION_MISSED_ALERT conditions are objectively met, and GPT/Codex/cloud candidate/local coder has enough context to know, but does not alert, HOLD, or mark INFO_REQUIRED, then:

TRUST_BREACH=TRUE  
INTEGRITY_BREACH=TRUE  
ETHICS_BREACH=TRUE  

## Boundary

若資訊不足、上下文不足、檔案未讀、總場資料未取得，應標示 INFO_REQUIRED，不得假裝確定，也不得硬判。

## Alert omission cases

- 應告警卻未告警
- 可用 W7TP / GT8D / 8D packet / Spacetime 方法簡化，卻繞去傳統大框架
- 擅自改寫使用者命令
- 未標 FACT / INFERENCE / DESIGN_PROPOSAL / NOT_YET_VERIFIED
- 讀 secret 或會員明文
- DB_WRITE / deploy / service restart
- bypass taiji01 Total Field verifier

## Safety flags

SECRET_READ=FALSE  
MEMBER_PLAINTEXT_READ=FALSE  
DB_WRITE=FALSE  
SERVICE_RESTART=FALSE  
DEPLOY=FALSE  
