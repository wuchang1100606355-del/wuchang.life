# Tensor Deadbox Route

## Definition

The Tensor Deadbox Route is the governed terminal route of Taiji Tensor Gateway.

It receives tensor packets that cannot be safely validated, routed, confirmed, executed, or completed.

## Trigger Conditions

A tensor packet enters the deadbox when any of the following occurs:

1. schema_invalid
2. node_offline
3. model_unavailable
4. timeout
5. permission_denied
6. confirmation_missing
7. risk_L3_forbidden
8. execution_failed
9. context_unrecoverable
10. replay_detected
11. stale_context
12. confirmation_expired
13. context_chain_broken
14. duplicate_task_id
15. pasted_output_as_command
16. deadbox_replay_attempt
17. node_reconnect_old_queue
18. expired_authorization_state

## Stored Fields

The deadbox stores:

- packet_hash
- task_id
- source_node
- target_node
- risk_level
- failure_reason
- retryable
- retry_after_seconds
- audit_id
- redacted_summary
- created_at

The deadbox must not store raw secrets, private keys, tokens, passwords, or unreduced sensitive context.

## Patent Value

The deadbox prevents failed AI tasks from disappearing, looping, executing unsafely, or leaking context.

It converts failure into an auditable routing state.
