# Context Replay Index

## Definition

Context Replay Index, CRI, is the anti-replay layer of Taiji Tensor Gateway.

It prevents stale context, duplicated tensor packets, reused confirmation tokens, old terminal output, offline queue replay, and deadbox replay attempts from being treated as fresh executable tasks.

## Protected Replay Types

1. duplicate_task_id
2. replay_detected
3. stale_context
4. confirmation_expired
5. context_chain_broken
6. duplicate_packet_hash
7. pasted_output_as_command
8. deadbox_replay_attempt
9. node_reconnect_old_queue
10. expired_authorization_state

## Replay Fields

Each tensor packet may include:

- context_id
- task_id
- packet_hash
- parent_hash
- nonce
- issued_at
- expires_at
- sequence
- max_replay
- seen_before

## Decision Rules

If packet_hash already exists, route to deadbox with replay_detected.

If task_id already exists and max_replay is 0, route to deadbox with duplicate_task_id.

If expires_at is older than current time, route to deadbox with confirmation_expired or stale_context.

If sequence is lower than the current context sequence, route to deadbox with stale_context.

If parent_hash does not match the latest accepted packet, route to deadbox with context_chain_broken.

If pasted terminal output is detected as executable input, classify it as pasted_output_as_command and prevent direct execution.

## Patent Value

The replay index transforms AI context replay from an accidental or adversarial execution risk into a governed routing state.

It ensures that AI tasks are validated not only by schema and authority, but also by freshness, uniqueness, sequence, and context-chain integrity.
