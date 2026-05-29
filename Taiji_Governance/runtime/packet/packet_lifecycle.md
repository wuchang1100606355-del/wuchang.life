# Packet Lifecycle

1. Observe request/event.
2. Redact or hash source content.
3. Build TensorPacket.
4. Validate packet schema.
5. Check replay index.
6. Check authority vector.
7. Check topology vector.
8. Classify risk.
9. Route action.
10. Append audit.
11. Preserve rollback horizon.

Packets that fail replay, authority, topology, or plaintext checks enter deadbox.
