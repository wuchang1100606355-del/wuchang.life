# Container Memory Policy

updated_at: 2026-06-21
status: READY_TO_APPLY_POLICY_ONLY
scope: W7TP / XiaoJ / Taiji_Hub local container memory governance
effect: documentation_policy_only_until_applied_to_compose_or_systemd

## Principle

大腦可以吃資源；
手臂不能爆衝；
嘴巴不能囤資料；
佇列不能無限長。

Translated engineering rule:

* Brain（大腦）= LLM / Ollama / GPU inference：先量測，不先硬限。
* Arm（手臂）= execution / browser / claw / tool runner：必須限資源。
* Mouth（嘴巴）= gateway / voice / text intake：不能囤積上下文與請求。
* Queue（佇列）= file queue / retry queue / resilience queue：必須有上限與 dead-letter。

## Policy Summary

STATE=READY_TO_APPLY
OLLAMA_HARD_CAP=FALSE
BROKER_GATEWAY_ADAPTER_CAP=TRUE
SECRET_READ=FALSE
MEMBER_PLAINTEXT_READ=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE

## Container Classes

### 1. wuchang_gpu_brain

role: Ollama / local GPU brain（本地 GPU 模型大腦）

policy:

* memory_limit: none_yet
* swap_limit: none_yet
* reason: LLM runtime（模型執行期）需要彈性 RAM / VRAM，過早限制會造成模型載入失敗或推理不穩。
* action: measure_first_then_cap

rules:

* Do not cap Ollama until real model load pattern is measured.
* Do not colocate uncontrolled tool execution inside this container.
* This container may consume memory, but it must not receive DB_WRITE / DEPLOY authority by default.

suggested_monitoring:

* record model name
* record load time
* record peak RAM
* record peak VRAM if available
* record failed model load
* record OOM event

future_cap_condition:

* only cap after at least 3 measured workloads:

  * small model
  * normal work model
  * largest expected model

### 2. open-webui

role: cockpit（操作座艙 / 使用者介面）

suggested_limits:

* memory: 6g
* swap: 8g

policy:

* allow file context / Knowledge / RAG（知識庫檢索）
* do not store credential JSON as Knowledge
* do not use as long-term queue
* do not use as secret vault
* keep citations / source refs enabled when possible

rules:

* File Upload = allowed
* File Context = allowed
* Knowledge = allowed
* credential plaintext = forbidden
* path_ref / hash_ref / manifest_ref = allowed

### 3. taiji_claw_safe

role: controlled execution arm（受控執行手臂）

suggested_limits:

* memory: 512m
* swap: 1g

policy:

* must be capped
* must not run unbounded browser / shell / automation loops
* must not directly deploy
* must not directly restart services unless explicitly authorized

rules:

* DB_WRITE=false by default
* SERVICE_RESTART=false by default
* DEPLOY=false by default
* PRODUCTION_RELEASE=false by default

### 4. taiji_pos_google_voice_tool

role: POS text intent gateway（POS 文字意圖入口）

suggested_limits:

* memory: 512m
* swap: 1g

policy:

* must be capped
* accepts text intent only
* should emit candidate_intent / candidate_delta
* must not directly create POS order unless local verifier approves

rules:

* raw audio storage: disabled by default
* member plaintext retention: disabled by default
* queue length: bounded
* failed request: dead_letter_queue

### 5. taiji_device_resilience_adapter

role: device queue / file resilience adapter（設備佇列與檔案韌性轉接器）

suggested_limits:

* memory: 512m
* swap: 1g

policy:

* must be capped
* queue must be bounded
* retry must be bounded
* failed item must go to dead_letter_queue

rules:

* no infinite retry
* no infinite queue
* no silent drop
* no plaintext member data unless explicitly classified and approved

## Default Resource Table

| Container                       | Role                     |   Memory |     Swap | Cap Required      |
| ------------------------------- | ------------------------ | -------: | -------: | ----------------- |
| wuchang_gpu_brain               | Ollama / local GPU brain | none_yet | none_yet | No, measure first |
| open-webui                      | cockpit                  |       6g |       8g | Yes               |
| taiji_claw_safe                 | controlled execution arm |     512m |       1g | Yes               |
| taiji_pos_google_voice_tool     | POS text intent gateway  |     512m |       1g | Yes               |
| taiji_device_resilience_adapter | device queue adapter     |     512m |       1g | Yes               |

## Runtime Boundary

Default forbidden unless explicitly authorized:

* DB_WRITE
* SERVICE_RESTART
* DEPLOY
* PRODUCTION_RELEASE
* POS_ACTION
* Odoo core mutation
* credential plaintext read
* member plaintext retention
* infinite browser control loop
* infinite queue
* infinite retry

Allowed by default:

* readonly diagnosis（唯讀診斷）
* path_ref（路徑參照）
* hash_ref（雜湊參照）
* manifest_ref（清單參照）
* runtime status（執行期狀態）
* git HEAD（目前提交）
* bounded queue inspection（有限佇列檢查）
* candidate_delta（候選狀態差分）
* dryrun（乾跑）
* local verifier（本地驗證）

## Queue Policy

queue_max_items:

* default: 1000
* high_volume_adapter: define explicitly before production

retry_policy:

* max_retry: 3
* backoff: exponential_or_fixed
* after_failed_retry: dead_letter_queue

dead_letter_required:

* true

dead_letter_record_must_include:

* packet_ref
* path_ref
* reason
* timestamp
* hash_ref if available
* secret_value_print=false

## Apply Rule

This policy does not change containers by itself.

To make it active, it must be applied to one of:

* docker compose memory limits
* systemd unit limits
* container runtime flags
* Kubernetes resource limits
* local supervisor config

Before applying:

STATE=PLAN_ONLY
VERIFY_CURRENT_CONTAINER_NAMES=TRUE
VERIFY_COMPOSE_PATH=TRUE
VERIFY_SERVICE_OWNERSHIP=TRUE
SECRET_READ=FALSE
DB_WRITE=FALSE
SERVICE_RESTART=FALSE
DEPLOY=FALSE

After applying:

STATE=APPLIED_ONLY_AFTER_HUMAN_AUTHORIZATION
VERIFY=docker inspect / docker stats / systemctl status
ROLLBACK=restore previous compose or systemd config

## Final Rule

Do not cap Ollama until model load pattern is measured.

Do cap broker / gateway / adapter / execution-arm containers.

Safety must be risk-tiered governance（分級風險治理）, not blanket shutdown（全部關閉）.
