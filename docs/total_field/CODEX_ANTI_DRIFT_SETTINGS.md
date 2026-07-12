# Codex Workspace Rules — Taiji_Hub

## Non-negotiable scope
- Do exactly the requested task.
- Do not expand scope.
- Do not refactor unrelated files.
- Do not rename files, move files, delete files, or overwrite original files unless explicitly requested.
- Do not run deploy, restart, reboot, router write, DB write, migration, public controller patch, or container direct patch.
- Do not expose secrets, tokens, passwords, member plaintext, raw private data, or raw credentials.
- Do not use `git add .`.

## W7TP / Total Field operating model
Use the 8-field packet mentally before editing:

D1 Intent: direct requested result.  
D2 State: existing PASS, run_id, terminal output, known files.  
D3 Coordinate: repo path, target file, module, node.  
D4 Evidence: current file contents, tests, reports, explicit terminal output.  
D5 Execution: shortest safe action.  
D6 Generative Transmission: state-field packet / references / lookup / reconstruction / verifier, not file moving or cloud sync.  
D7 Risk: only real hard risks.  
D8 Envelope: short, complete, reviewable output.

## Anti-drift rule
If the task is direct and no hard risk is hit:
- perform the shortest safe edit.
- do not ask unnecessary questions.
- do not perform unrelated scans.
- do not create broad architecture unless asked.

If an existing PASS / run_id / terminal output is provided:
- do not rerun the same stage.
- do not re-scan unless the user asks.
- continue from NEXT.

If drift is detected, output:
STATE=HOLD_DETOUR_ALERT
decision=Detected scope drift or technical-definition drift. Previous path invalid.
next=Return to shortest direct result or list only true hard risks.

## Coding precision rules
Before modifying code:
1. Read the target file.
2. Identify exact function/class/block.
3. Patch only that exact area.
4. Preserve existing imports, naming, style, and public API unless asked.
5. Do not invent non-existing APIs.
6. Do not assume Odoo model fields exist; verify by grep/read first.
7. Do not modify database schema unless explicitly requested.
8. For Python, run `python3 -m py_compile` on changed Python files when possible.
9. For shell, run `bash -n` on changed shell scripts when possible.
10. For JS/HTML/CSS, validate by static grep and syntax where available.

## Output format
Always end with:
STATE=<PASS/HOLD>
FILES_CHANGED=<list>
VALIDATION=<commands run / not run with reason>
NEXT=<one next action>

## Forbidden unless explicitly requested
- deploy
- restart
- reboot
- docker compose restart/up/down
- Odoo module upgrade
- DB write
- migration
- router write
- moving/deleting original files
- public release
- sending email
- publishing website
- exposing raw secret/member/plaintext data

## Website / public copy rules
Must use:
- 免費訂閱
- 生成式傳輸測試
- 聊國咖啡館老闆的私家傳輸技術
- 小傳輸量，可產生大檔案結果
- 以 AI 科技抵禦 AI 時代的衝擊，以科技服務社區
- 不募款
- 婉謝捐款
- 以商以智養公益
- 聘請照服員
- 辦志工隊
- 社區數位發展基金

Must not use:
- 免費免訂閱
- 高利息債務
- 還債
- 養員工
- 員工獎金
- 已核准發明專利
- Google 背書
- 政府背書
- 任意檔案都能小封包下載
