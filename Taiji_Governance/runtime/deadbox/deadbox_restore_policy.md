# Deadbox Restore Policy

Deadbox packets may not re-enter runtime directly.

Restore requires:

1. redacted audit review
2. authority regeneration
3. replay reset
4. topology verification
5. new TensorPacket generation
6. human approval for L2/L3

Restore is forbidden if the packet requires secret disclosure, cloud plaintext, or production mutation without an approved runtime.
