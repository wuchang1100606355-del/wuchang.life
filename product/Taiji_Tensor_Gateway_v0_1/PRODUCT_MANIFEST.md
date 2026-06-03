# Taiji Tensor Gateway v0.1

## Product Name

Taiji Tensor Gateway

## Core Engine

Five-Dimensional Metric Tensor Ramp Translation Engine

## Product Category

Governed Distributed AI Runtime

## Product Definition

Taiji Tensor Gateway is a governed distributed AI runtime that converts natural language input, system events, and operational requests into five-dimensional metric tensor packets.

Each tensor packet is validated, checked against replay risks, routed through a governance layer, and dispatched to the lowest-cost, lowest-memory-I/O, lowest-wake-cost, and lowest-risk execution path across distributed AI nodes.

## Core Pipeline

User Input / System Event  
→ Metric Ramp Translator  
→ Five-Dimensional Metric Tensor Packet  
→ Schema Validator  
→ Context Replay Index  
→ Dispatch Engine  
→ Governance Layer  
→ Worker / Confirmation / Rejection / Deadbox  
→ Metrics Feedback  
→ Replay Index Update

## Five Tensor Dimensions

1. Intent  
   The purpose of the task.

2. Resource  
   CPU, RAM, GPU, model tier, memory pressure, model load cost, and I/O cost.

3. Time  
   Urgency, uptime requirement, wake cost, expiration, and latency target.

4. Authority  
   Risk level, confirmation requirement, audit requirement, and execution boundary.

5. Topology  
   Node selection, network path, data locality, fallback route, and temporary worker status.

## Default Node Roles

- taiji01: always-on anchor, registry, dispatch controller, Odoo/database host, 1.5B tensor translator node, primary low-cost worker.
- penguin: lightweight Ollama worker, fallback inference worker, suitable for 4B-level tasks.
- MSI: temporary GPU worker, Open WebUI cockpit, Claw governance interface, high-reasoning model node, not always-on.

## Risk Levels

- L0_readonly
- L1_low
- L2_confirm
- L3_forbidden

## Product Boundary

This product is not a chatbot.

It is a governed AI runtime gateway that transforms language into validated, replay-protected, tensor-routed execution.
