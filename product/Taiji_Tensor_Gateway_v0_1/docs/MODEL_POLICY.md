# Tensor Model Policy

## Default Tensor Translator

Model: qwen2.5-coder:1.5b  
Node: taiji01  
Purpose: metric ramp translation and five-dimensional tensor packet generation.

## Fallback Worker

Model: gemma3:4b  
Node: penguin  
Purpose: lightweight generation and fallback reasoning.

## High Reasoning Worker

Model: metric-language-gateway-ai:latest  
Node: MSI  
Purpose: complex reasoning, patent drafting, whitepaper drafting, and architecture review.  
Policy: use only when MSI is online and escalation is necessary.

## Rule

Never use an 8B model for routine tensor routing unless escalation is required.
