# D8 Three Minute Demo Script

## 0:00-0:30 Status And Doctor

Run:

```bash
tools/d8_product_demo_launcher.sh status
tools/d8_product_demo_launcher.sh doctor
```

Show that D8 memory, redteam events, possible alerts, and guard evaluations are already indexed locally.

## 0:30-1:00 Alerts And Redteam

Run:

```bash
tools/d8_total_field_console.sh alerts
tools/d8_total_field_console.sh redteam
```

Explain that redteam evidence is non-executable and isolated from safe memory.

## 1:00-1:30 Safe Preflight

Run:

```bash
tools/d8_total_field_console.sh preflight --task-name SAFE_TOTAL_FIELD_STATUS_READ --mode sandbox --scope-json '{"readonly":true,"target":"d8_total_field_current_status"}'
```

Show PASS before action.

## 1:30-2:00 WARN Boundary

Run a scope with pre-existing non-D8 diff and explain that AGENTS.md is recorded as a warning rather than automatically modified or reverted.

## 2:00-2:30 Voice/Text Operator

Run:

```bash
tools/d8_product_demo_launcher.sh voice-demo --text "查狀態" --dry-run
tools/d8_product_demo_launcher.sh voice-demo --text "看告警" --dry-run
```

Show routing without microphone access, raw audio storage, or external STT.

## 2:30-3:00 Odoo/POS Safe Bridge

Run:

```bash
tools/d8_product_demo_launcher.sh pos-bridge-demo --dry-run
```

Show read-only manifest mode: no order, no payment, no Odoo DB write, no production DB write.
