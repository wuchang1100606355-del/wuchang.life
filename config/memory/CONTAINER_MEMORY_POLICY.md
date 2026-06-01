# Container Memory Policy

updated_at: 2026-05-07
status: DRAFT_READY_TO_APPLY

## Principle

大腦可以吃資源；
手臂不能爆衝；
嘴巴不能囤資料；
佇列不能無限長。

## Policy

wuchang_gpu_brain:
- role: Ollama / local GPU brain
- policy: no hard memory cap yet
- reason: LLM runtime needs flexible RAM / VRAM

open-webui:
- role: cockpit
- suggested memory: 6g
- suggested swap: 8g

taiji_claw_safe:
- role: controlled execution arm
- suggested memory: 512m
- suggested swap: 1g

taiji_pos_google_voice_tool:
- role: POS text intent gateway
- suggested memory: 512m
- suggested swap: 1g

taiji_device_resilience_adapter:
- role: device queue / file resilience adapter
- suggested memory: 512m
- suggested swap: 1g

## Rule

Do not cap Ollama until model load pattern is measured.
Do cap broker / gateway / adapter containers.
