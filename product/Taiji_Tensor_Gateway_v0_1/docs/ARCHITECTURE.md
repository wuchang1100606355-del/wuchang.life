# Taiji Tensor Gateway Architecture

## Runtime Pipeline

User Input  
→ Metric Ramp Translator  
→ Five-Dimensional Metric Tensor Packet  
→ Schema Validator  
→ Context Replay Index  
→ Dispatch Engine  
→ Governance Layer  
→ Worker / Confirmation / Rejection / Deadbox  
→ Metrics Feedback  
→ Replay Index Update

## Metric Ramp Translator

The Metric Ramp Translator converts human language, system events, terminal observations, operational requests, and AI tool requests into structured tensor packets.

It does not execute commands.

It produces a machine-facing tensor packet that can be validated, routed, audited, rejected, or placed into the deadbox.

## Five-Dimensional Metric Tensor Topology

The tensor topology represents each task using five dimensions:

1. Intent
2. Resource
3. Time
4. Authority
5. Topology

This allows the runtime to decide whether a task should be handled by an always-on anchor node, a lightweight worker, a temporary GPU worker, a governance queue, or a deadbox route.

## Node Policy

- taiji01 is the always-on anchor node.
- penguin is the lightweight worker.
- MSI is the temporary GPU worker and cockpit.
- MSI must not be required for low-level routing tasks.
- 8B models must not be used for routine tensor routing unless escalation is required.

## Governance Boundary

AI does not directly execute high-risk operations.

Tasks must pass through tensor validation, replay protection, risk classification, and governance routing.
