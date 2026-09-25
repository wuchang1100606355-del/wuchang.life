# 總場非浮點確定性 AI 與主動問題封包

## 正式定義

總場核心是非浮點確定性 AI，而不是 LLM 或自由文字推論器：

```text
非浮點確定性 AI
＋狀態場查表
＋規則推演
＋整數及位元索引
＋雜湊與狀態機
＋多層稽核
＋候選比較
＋主動問題發現
＋驗證與封印
```

固定屬性：

```text
NO_GENERATIVE_TOKEN_INFERENCE_REQUIRED=TRUE
NO_LLM_HALLUCINATION_BY_DESIGN=TRUE
DETERMINISTIC_CORE=TRUE
ACTIVE_PROBLEM_DISCOVERY=TRUE
ENGINEERING_ERROR_AUDIT_REQUIRED=TRUE
```

「無 LLM 式幻覺」不代表無錯誤。每次判定仍須檢查規則版本、錯誤輸入、程式 bug 證據、過期查表、多層稽核及封套完整性。

## 確定性流程

```text
PACKET
  → SCHEMA
  → STATE_LOOKUP
  → RULE_MATCH
  → CONDITION_EXPANSION
  → EVIDENCE_CHECK
  → COMPARE
  → DECISION
  → SEAL
```

核心只使用已版本化規則、明確狀態欄位、集合關係、整數序位、位元旗標與 canonical JSON SHA256。相同輸入與相同規則版本必須產生相同 packet identifier、問題順序、SHA256 與決策。

## 主動問題觸發表

主動問題不是自由文字猜測，只能由下列明確缺口集合非空時觸發：

| 缺口欄位 | 問題封包類型 | question code |
|---|---|---|
| `missing_state_refs` | `MISSING_STATE_QUESTION_PACKET` | `PROVIDE_REQUIRED_STATE_REFS` |
| `conflicting_evidence_refs` | `EVIDENCE_CONFLICT_QUESTION_PACKET` | `RESOLVE_EVIDENCE_CONFLICT_REFS` |
| `authority_conflict_refs` | `AUTHORITY_CLARIFICATION_PACKET` | `CLARIFY_AUTHORITY_REFS` |
| `reconstruction_gap_refs` | `RECONSTRUCTION_GAP_PACKET` | `PROVIDE_RECONSTRUCTION_CONDITIONS` |
| `unresolved_route_refs` | `UNRESOLVED_ROUTE_PACKET` | `RESOLVE_ROUTE_REFS` |
| `unmatched_condition_refs` | `NEW_RULE_CANDIDATE_PACKET` | `REVIEW_NEW_RULE_CANDIDATE` |

每個問題封包固定為 `STATE=HOLD`、`SEAL_STATUS=NOT_SEALED`、`execution_authority=false`。若所有缺口集合都空，主動問題結果為 PASS，但這不自動代表候選可封印；候選仍須完成其餘治理稽核。

## 規則與工程錯誤稽核

輸入必須攜帶 `rule_version`、`lookup_version`、`input_valid`、`bug_evidence_refs` 與六類缺口集合。下列任一情況必須 HOLD：

- 規則版本不是 runtime 支援版本。
- lookup version 已過期或未支援。
- `input_valid=false`。
- `bug_evidence_refs` 非空。
- 任一缺口觸發主動問題封包。

問題封包本身只能描述缺口 reference、要求的回應欄位、authority scope 與 evidence reference；不得內嵌會員明文、完整本地狀態或自由文字猜測。

## 封印邊界

未驗證候選、L3 candidate、存在 active question、規則／lookup 不相容或工程錯誤證據時均不得 SEAL。只有 schema、state lookup、rule match、condition expansion、evidence check、compare 及全部治理稽核通過後，才能進入獨立 seal gate。

總場可以獨立產生與比較候選，但不能擅自啟動小J；服務帳戶只是雲端 connector identity，不是總場大腦、Owner 意圖、小J身分或最終裁決權。
