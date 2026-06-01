# Replay And Deadbox Risk Matrix

| Signal | Risk | Default action | Recovery |
| --- | --- | --- | --- |
| packet hash duplicate with same nonce | L2 | quarantine | replay reset |
| packet hash duplicate with changed authority | L3 | deadbox | human approval |
| parent hash missing | L2 | warn/block | audit review |
| expired execution window | L2 | deadbox if executable | regenerate packet |
| stale topology | L2/L3 | quarantine/deadbox | topology verification |
| deadbox packet submitted directly | L3 | block | restore policy |
| payment replay | L3 | deadbox | separate human-governed runtime |
| deployment replay | L3 | deadbox | new preflight + human decision |
| multimodal replay with sensitive content | L3 | deadbox | redaction and reclassification |
