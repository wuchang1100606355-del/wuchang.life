# Implementation Examples

## Example 1: Three-Node Distributed AI Runtime

The system may include:

1. taiji01  
   Always-on anchor node, registry, dispatch controller, Odoo/database host, and 1.5B tensor translator.

2. penguin  
   Lightweight worker node and fallback inference endpoint.

3. MSI  
   Temporary GPU worker, Open WebUI cockpit, Claw governance interface, and high-reasoning model node.

## Example 2: Low-Risk System Probe

Input:

"Probe the distributed compute status of taiji01, penguin, and MSI without modifying the system."

Generated tensor packet:

- intent.type = system_status_probe
- resource.gpu_required = false
- authority.risk = L0_readonly
- topology.primary = taiji01
- topology.fallback = penguin
- topology.temporary = MSI
- decision = dry_run

The system does not wake MSI GPU and does not load a large model.

## Example 3: High-Reasoning Architecture Review

Input:

"Review this distributed AI runtime architecture for patent packaging."

Generated tensor packet:

- intent.type = architecture_review
- resource.model_tier = 8b
- resource.gpu_required = true
- authority.risk = L1_low or L2_confirm
- topology.temporary = MSI
- decision = route_to_worker or ask_confirm

If MSI is online and authorization passes, the task may be escalated to the temporary GPU worker.

## Example 4: Context Replay Prevention

If a previously executed packet is pasted again as a new request, the replay index detects an existing packet hash or stale sequence number.

The task is not executed.

It is routed to the Tensor Deadbox Route with failure_reason = replay_detected or pasted_output_as_command.
