# Redteam Paste Integrity Gate（紅隊貼上完整性閘）

RUN_ID=REDTEAM_PASTE_INTEGRITY_GATE_20260613_064516
STATE=REDTEAM_PASTE_INTEGRITY_GATE_READY

## Incident（事件）
- Prior operations reached PASS, but paste contamination appeared in terminal input.
- Examples: shortset, parse residue, broken command tail, unexpected text inserted into command stream.
- Impact: no security/compliance bypass observed, but operational trust was degraded.

## Classification（分類）
- REDTEAM_PARTIAL_FAIL
- TYPE=PASTE_INTEGRITY_GATE_MISSED
- SEVERITY=MEDIUM
- WINDOW=W0/W1/W2/W3 operational safety

## Hard HOLD Triggers（硬性 HOLD 條件）
- shell continuation prompt: >
- broken heredoc
- unexpected command tail
- git status --shortset
- } parse residue
- mixed cleanup plus deploy in one command
- command text visually contaminated after paste

## Required Action（必要動作）
- Stop current operation.
- Do not continue deployment or commit.
- Run readonly verify only.
- Resume only after clean prompt, clean worktree, and exact staged-file check.

## New Rule（新規則）
- Use subshell for interactive taiji01 commands: ( set -euo pipefail ... ).
- Avoid long heredoc in user-paste workflows.
- Host Gate, Repo Gate, Branch Gate, Dirty Worktree Gate, Gitignore Gate, Secret/PII Gate, One-Task Gate, Verify-before-Commit Gate remain mandatory.

## Final Sentence（核心句）
結果 PASS 不代表流程乾淨；貼上污染一律 HOLD，先驗證再續行。
